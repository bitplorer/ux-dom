from ux_dom import Component, Document
from ux_dom.dom import a, div, h1, li, p, ul

__all__ = ['Index']


class Index(Component):
    routes = ["get"]

    def render(self):
        return div(
            h1("UxDom Hypermedia Shop"),
            p("Pure ux_dom — DirectoryRouter + HTMX + Components."),
            ul(
                li(a("Product list", href="/shop/products/list/ProductList")),
                li(a("Cart counter", href="/shop/cart/counter/CartCounter")),
            ),
            id="home",
            className="page",
        )

    @classmethod
    def get(cls):
        return Document(ensure_csrf_token=False)(cls())
