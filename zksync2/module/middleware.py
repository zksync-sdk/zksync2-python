from web3.middleware import Web3Middleware


class ZkSyncMiddlewareBuilder(Web3Middleware):
    def wrap_make_request(self, make_request):
        def middleware(method, params):
            return make_request(method, params)

        return middleware
