from sanic import Sanic
from sanic.response import text
from sanic_plugin_toolkit import SanicPluginRealm
from sanic_plugin_toolkit.plugins.contextualize import instance as contextualize
app = Sanic(__name__)
realm = SanicPluginRealm(app)


@contextualize.listener('after_server_start')
async def setup_db(app, loop, context):
    from sqlalchemy import create_engine
    shared_context = context.shared
    engine = create_engine('sqlite:///orm_in_detail.sqlite')
    shared_context['db'] = engine
    from sqlalchemy.orm import sessionmaker
    session = sessionmaker()
    session.configure(bind=engine)
    shared_context['dbsession'] = session


async def get_user_session(db_session):
    # Hypothetical get_user_session function
    return {"username": "test_user"}


@contextualize.middleware(priority=4)
async def db_request_middleware(request, context):
    shared_context = context.shared
    request_context = shared_context.request
    db_session = shared_context.dbsession
    user_session = await get_user_session(db_session)
    request_context['user_session'] = user_session


@contextualize.route('/')
def index(request, context):
    shared_context = context.shared
    request_context = shared_context.request
    user_session = request_context.user_session
    current_username = user_session['username']
    return text("hello {}!".format(current_username))


_ = realm.register_plugin(contextualize)

if __name__ == "__main__":
    app.run("127.0.0.1", port=8098, debug=True, auto_reload=False)
