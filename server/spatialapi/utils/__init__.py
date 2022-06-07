from flask import make_response, jsonify
import logging

logger = logging.getLogger(__name__)


def json_error(message: str, error_code: int):
    logger.error(f'JSON_ERROR Response; message: {message}; error_code: {error_code}')
    return make_response(jsonify(message=message), error_code)
