from sanic import Blueprint

api_v1 = Blueprint(__name__, None)


@api_v1.middleware(attach_to="request")
async def bp_mw(request):
    print("Hello bp")

__all__ = ['api_v1']
