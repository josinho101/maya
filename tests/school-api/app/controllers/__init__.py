class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


class ServerError(Exception):
    pass


def paginate(items, args):
    page_raw = args.get("page", "1")
    page_size_raw = args.get("page_size", "10")

    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
    except (TypeError, ValueError):
        raise BadRequest("page and page_size must be integers")

    if page < 1 or page_size < 1:
        raise BadRequest("page and page_size must be positive integers")

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }
