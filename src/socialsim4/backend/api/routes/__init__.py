from litestar import Router

from . import admin, auth, config, providers, scenes, simulations, search_providers


router = Router(
    path="",
    route_handlers=[
        auth.router,
        config.router,
        scenes.router,
        simulations.router,
        providers.router,
        search_providers.router,
        admin.router,
    ],
)
