import inspect
import os

from time import gmtime, strftime

import pytest

from sanic_plugin_toolkit import SanicPlugin


class TestPlugin(SanicPlugin):
    pass


# The following tests are taken directly from Sanic source @ v0.8.2
# and modified to test the SanicPlugin, rather than Sanic

# ------------------------------------------------------------ #
#  GET
# ------------------------------------------------------------ #


@pytest.fixture(scope="module")
def static_file_directory():
    """The static directory to serve"""
    current_file = inspect.getfile(inspect.currentframe())
    current_directory = os.path.dirname(os.path.abspath(current_file))
    static_directory = os.path.join(current_directory, "static")
    return static_directory


def get_file_path(static_file_directory, file_name):
    return os.path.join(static_file_directory, file_name)


def get_file_content(static_file_directory, file_name):
    """The content of the static file to check"""
    with open(get_file_path(static_file_directory, file_name), "rb") as file:
        return file.read()


@pytest.fixture(scope="module")
def large_file(static_file_directory):
    large_file_path = os.path.join(static_file_directory, "large.file")

    size = 2 * 1024 * 1024
    with open(large_file_path, "w") as f:
        f.write("a" * size)

    yield large_file_path

    os.remove(large_file_path)


@pytest.fixture(autouse=True, scope="module")
def symlink(static_file_directory):
    src = os.path.abspath(os.path.join(os.path.dirname(static_file_directory), "conftest.py"))
    symlink = "symlink"
    dist = os.path.join(static_file_directory, symlink)
    try:
        os.remove(dist)
    except FileNotFoundError:
        pass
    os.symlink(src, dist)
    yield symlink
    os.remove(dist)


@pytest.fixture(autouse=True, scope="module")
def hard_link(static_file_directory):
    src = os.path.abspath(os.path.join(os.path.dirname(static_file_directory), "conftest.py"))
    hard_link = "hard_link"
    dist = os.path.join(static_file_directory, hard_link)
    try:
        os.remove(dist)
    except FileNotFoundError:
        pass
    os.link(src, dist)
    yield hard_link
    os.remove(dist)


@pytest.mark.parametrize(
    "file_name",
    ["test.file", "decode me.txt", "python.png", "symlink", "hard_link"],
)
def test_static_file(realm, static_file_directory, file_name):
    app = realm._app
    plugin = TestPlugin()
    plugin.static("/testing.file", get_file_path(static_file_directory, file_name))
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get("/testing.file")
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)


@pytest.mark.parametrize("file_name", ["test.html"])
def test_static_file_content_type(realm, static_file_directory, file_name):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        content_type="text/html; charset=utf-8",
    )
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get("/testing.file")
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt", "symlink", "hard_link"])
@pytest.mark.parametrize("base_uri", ["/static", "", "/dir"])
def test_static_directory(realm, file_name, base_uri, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(base_uri, static_file_directory)
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get(uri="{}/{}".format(base_uri, file_name))
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_head_request(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.head("/testing.file")
    assert response.status == 200
    assert "Accept-Ranges" in response.headers
    assert "Content-Length" in response.headers
    assert int(response.headers["Content-Length"]) == len(get_file_content(static_file_directory, file_name))


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_correct(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    headers = {"Range": "bytes=12-19"}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)
    assert response.status == 206
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    static_content = bytes(get_file_content(static_file_directory, file_name))[12:20]
    assert int(response.headers["Content-Length"]) == len(static_content)
    assert response.body == static_content


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_front(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    headers = {"Range": "bytes=12-"}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)
    assert response.status == 206
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    static_content = bytes(get_file_content(static_file_directory, file_name))[12:]
    assert int(response.headers["Content-Length"]) == len(static_content)
    assert response.body == static_content


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_back(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    headers = {"Range": "bytes=-12"}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)
    assert response.status == 206
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    static_content = bytes(get_file_content(static_file_directory, file_name))[-12:]
    assert int(response.headers["Content-Length"]) == len(static_content)
    assert response.body == static_content


@pytest.mark.parametrize("use_modified_since", [True, False])
@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_empty(realm, file_name, static_file_directory, use_modified_since):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
        use_modified_since=use_modified_since,
    )
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get("/testing.file")
    assert response.status == 200
    assert "Content-Length" in response.headers
    assert "Content-Range" not in response.headers
    assert int(response.headers["Content-Length"]) == len(get_file_content(static_file_directory, file_name))
    assert response.body == bytes(get_file_content(static_file_directory, file_name))


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_error(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    headers = {"Range": "bytes=1-0"}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)
    assert response.status == 416
    assert "Content-Length" in response.headers
    assert "Content-Range" in response.headers
    assert response.headers["Content-Range"] == "bytes */%s" % (
        len(get_file_content(static_file_directory, file_name)),
    )


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_unit(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    unit = "bit"
    headers = {"Range": "{}=1-0".format(unit)}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert "{} is not a valid Range Type".format(unit) in response.text


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_start(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    start = "start"
    headers = {"Range": "bytes={}-0".format(start)}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert "'{}' is invalid for Content Range".format(start) in response.text


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_end(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    end = "end"
    headers = {"Range": "bytes=1-{}".format(end)}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert "'{}' is invalid for Content Range".format(end) in response.text


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt"])
def test_static_content_range_invalid_parameters(realm, file_name, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_content_range=True,
    )
    realm.register_plugin(plugin)
    headers = {"Range": "bytes=-"}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)

    assert response.status == 416
    assert "Invalid for Content Range parameters" in response.text


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt", "python.png"])
def test_static_file_specified_host(realm, static_file_directory, file_name):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        host="www.example.com",
    )
    realm.register_plugin(plugin)
    headers = {"Host": "www.example.com"}
    request, response = app._test_manager.test_client.get("/testing.file", headers=headers)
    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)
    request, response = app._test_manager.test_client.get("/testing.file")
    assert response.status == 404


@pytest.mark.parametrize("use_modified_since", [True, False])
@pytest.mark.parametrize("stream_large_files", [True, 1024])
@pytest.mark.parametrize("file_name", ["test.file", "large.file"])
def test_static_stream_large_file(
    realm,
    static_file_directory,
    file_name,
    use_modified_since,
    stream_large_files,
    large_file,
):
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_modified_since=use_modified_since,
        stream_large_files=stream_large_files,
    )
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get("/testing.file")

    assert response.status == 200
    assert response.body == get_file_content(static_file_directory, file_name)


@pytest.mark.parametrize("file_name", ["test.file", "decode me.txt", "python.png"])
def test_use_modified_since(realm, static_file_directory, file_name):

    file_stat = os.stat(get_file_path(static_file_directory, file_name))
    modified_since = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(file_stat.st_mtime))
    app = realm._app
    plugin = TestPlugin()
    plugin.static(
        "/testing.file",
        get_file_path(static_file_directory, file_name),
        use_modified_since=True,
    )
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get(
        "/testing.file", headers={"If-Modified-Since": modified_since}
    )

    assert response.status == 304


def test_file_not_found(realm, static_file_directory):
    app = realm._app
    plugin = TestPlugin()
    plugin.static("/static", static_file_directory)
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get("/static/not_found")

    assert response.status == 404
    assert "File not found" in response.text


@pytest.mark.parametrize("static_name", ["_static_name", "static"])
@pytest.mark.parametrize("file_name", ["test.html"])
def test_static_name(realm, static_file_directory, static_name, file_name):
    app = realm._app
    plugin = TestPlugin()
    plugin.static("/static", static_file_directory, name=static_name)
    realm.register_plugin(plugin)
    request, response = app._test_manager.test_client.get("/static/{}".format(file_name))

    assert response.status == 200
