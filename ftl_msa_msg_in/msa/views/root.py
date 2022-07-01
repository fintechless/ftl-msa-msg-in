"""
Flask view for the MSG IN blueprint
Path: /
"""

from flask import Response
from flask import make_response
from flask import request
from flask import session
from ftl_python_lib.constants.models.mapping import ConstantsMappingSourceType
from ftl_python_lib.core.context.environment import EnvironmentContext
from ftl_python_lib.core.context.request import REQUEST_CONTEXT_SESSION
from ftl_python_lib.core.context.request import RequestContext
from ftl_python_lib.core.exceptions.client_invalid_request_exception import ExceptionInvalidRequest
from ftl_python_lib.core.exceptions.client_resource_not_found_exception import ExceptionResourceNotFound
from ftl_python_lib.core.exceptions.server_unexpected_error_exception import ExceptionUnexpectedError
from ftl_python_lib.core.log import LOGGER
from ftl_python_lib.core.microservices.api.mapping import MicroserviceApiMapping
from ftl_python_lib.core.microservices.api.mapping import MircoserviceApiMappingResponse
from ftl_python_lib.core.microservices.which import which_microservice_am_i
from ftl_python_lib.core.providers.aws.s3 import ProviderS3
from ftl_python_lib.models.transaction import ModelTransaction
from ftl_python_lib.models_helper.message import HelperMessage
from ftl_python_lib.typings.iso20022.received_message import TypeReceivedMessage
from ftl_python_lib.utils.mime import mime_is_json
from ftl_python_lib.utils.mime import mime_is_xml
from ftl_python_lib.utils.xml.validation import UtilsXmlValidation

from ftl_msa_msg_in.msa.blueprints import BLUEPRINT_MSG_IN


@BLUEPRINT_MSG_IN.route("", methods=["POST"])
def post() -> Response:
    """
    Process POST request for the /msa/in endpoint
    Send new transaction
    """

    request_context: RequestContext = session.get(REQUEST_CONTEXT_SESSION)
    environ_context: EnvironmentContext = EnvironmentContext()

    if len(request.data) == 0 or request.data is None:
        LOGGER.logger.error("Missing message body")
        raise ExceptionInvalidRequest(
            message="Missing message body", request_context=request_context
        )
    if (
        request_context.transaction_id is None
        or request_context.headers_context.transaction_id is None
    ):
        LOGGER.logger.error("Missing X-Transaction-Id HTTP header")
        raise ExceptionInvalidRequest(
            message="Missing X-Transaction-Id HTTP header",
            request_context=request_context,
        )

    LOGGER.logger.debug(
        "\n".join(
            [
                "Proccessing POST request for MSG IN microservice",
                f"Request ID is {request_context.request_id}",
                f"Transaction ID is {request_context.transaction_id}",
                f"Request timestamp is {request_context.requested_at_datetime}",
            ]
        )
    )

    incoming: TypeReceivedMessage = TypeReceivedMessage(
        request_context=request_context,
        environ_context=environ_context,
        message_raw=request.data,
        content_type=request_context.headers_context.content_type,
    )

    try:
        incoming.fill_message_xml()
        incoming.fill_message_proc()
        incoming.fill_message_type()
        incoming.fill_message_version()
        incoming.fill_message_version_keys()
    except ValueError as exception:
        LOGGER.logger.error(exception)
        raise ExceptionInvalidRequest(
            message="Received an invalid incoming message",
            request_context=request_context,
        ) from exception

    # Required models and providers
    transaction: ModelTransaction = ModelTransaction(
        request_context=request_context, environ_context=environ_context
    )
    message: HelperMessage = HelperMessage(
        request_context=request_context, environ_context=environ_context
    )
    storage: ProviderS3 = ProviderS3(
        request_context=request_context, environ_context=environ_context
    )
    mapping: MicroserviceApiMapping = MicroserviceApiMapping(
        request_context=request_context, environ_context=environ_context
    )

    try:
        incoming.upload_to_storage(incoming=True)

        if not transaction.is_transaction_initiated():
            LOGGER.logger.error("Could not find such transaction")
            raise ExceptionResourceNotFound(
                message="Could not find such transaction",
                request_context=request_context,
            )

        message_definition = message.get_by_key(
            unique_type=incoming.message_version_keys.unique_type,
            version_major=incoming.message_version_keys.version_major,
            version_minor=incoming.message_version_keys.version_minor,
            version_patch=incoming.message_version_keys.version_patch,
        )
        xsd_body: bytes = storage.get_object_body(
            bucket=environ_context.runtime_bucket, key=message_definition.storage_path
        )
        with UtilsXmlValidation(xsd=xsd_body, xml=incoming.message_xml) as uxml:
            if uxml.is_valid() is False:
                LOGGER.logger.error("Received an invalid XML message")
                raise ExceptionInvalidRequest(
                    message="Received an invalid XML message",
                    request_context=request_context,
                )

        transaction.receive(
            storage_path=incoming.storage_path.key,
            message_type=incoming.message_version,
        )
        mapping_response: MircoserviceApiMappingResponse = mapping.get(
            params={
                "source_type": ConstantsMappingSourceType.SOURCE_TYPE_MESSAGE_IN.value,
                "source": ConstantsMappingSourceType.SOURCE_MESSAGE_IN.value,
                "content_type": incoming.content_type,
                "message_type": incoming.message_type,
            }
        )

        for mapping_item in mapping_response.data:
            target: str = mapping_item.target

            LOGGER.logger.debug("Sending new request to target '{target}'")

            microservice_instance = which_microservice_am_i(name=target)(
                request_context=request_context, environ_context=environ_context
            )

            if mime_is_xml(mime=incoming.content_type):
                LOGGER.logger.debug("Sending new request to target as XML")
                microservice_instance.post(
                    data=incoming.message_xml,
                    headers=request_context.headers_context.request_headers,
                )
            if mime_is_json(mime=incoming.content_type):
                LOGGER.logger.debug("Sending new request to target as JSON")
                microservice_instance.post(
                    data=incoming.message_proc,
                    headers=request_context.headers_context.request_headers,
                )

        return make_response(
            {
                "request_id": request_context.request_id,
                "status": "OK",
                "message": "Request was received",
            },
            200,
        )
    except (ExceptionInvalidRequest, ExceptionResourceNotFound) as exception:
        LOGGER.logger.error(exception)
        if request_context.transaction_id is not None:
            transaction.reject(
                storage_path=incoming.storage_path.key,
                message_type=incoming.message_version,
            )

        mapping_response: MircoserviceApiMappingResponse = mapping.get(
            params={
                "source_type": ConstantsMappingSourceType.SOURCE_TYPE_MESSAGE_IN.value,
                "source": ConstantsMappingSourceType.SOURCE_MESSAGE_OUT.value,
                "content_type": incoming.content_type,
                "message_type": incoming.message_type_out_failed,
            }
        )

        for mapping_item in mapping_response.data:
            target: str = mapping_item.target

            LOGGER.logger.debug("Sending new request to target '{target}'")

            microservice_instance = which_microservice_am_i(name=target)(
                request_context=request_context, environ_context=environ_context
            )

            if mime_is_xml(mime=incoming.content_type):
                LOGGER.logger.debug("Sending new request to target as XML")
                microservice_instance.post(
                    data=incoming.message_xml,
                    headers=request_context.headers_context.request_headers,
                )
            if mime_is_json(mime=incoming.content_type):
                LOGGER.logger.debug("Sending new request to target as JSON")
                microservice_instance.post(
                    data=incoming.message_proc,
                    headers=request_context.headers_context.request_headers,
                )

        raise exception
    except Exception as exception:
        LOGGER.logger.error(exception)
        raise ExceptionUnexpectedError(
            message=f"Unexpected server error: {exception}",
            request_context=request_context,
        ) from exception
