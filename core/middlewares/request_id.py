from uuid import uuid4


class RequestIdMiddleware:
    """
    Добавляет уникальный идентификатор запроса.

    Идентификатор сохраняется в `request.request_id` и возвращается в
    заголовке ответа `X-Request-ID`.
    """
    header_name = "X-Request-ID"
    meta_header_name = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(self.meta_header_name) or uuid4().hex
        request.request_id = request_id
        response = self.get_response(request)
        response[self.header_name] = request_id
        return response
