"""
Tests for MSA MSG IN, part of the PLATFORM category
"""


import json
import uuid
from typing import Any
from typing import Dict

from flask.testing import FlaskClient
from ftl_python_lib.models.transaction import ModelTransaction
from ftl_python_lib.typings.models.transaction import TypeTransaction
from werkzeug.test import TestResponse

MSA_IN_URL: str = "/msa/in"


# pylint: disable=R0903
class TestMsaMsgIn:
    """
    Test class for testing MSA MSG IN
    """

    @staticmethod
    def test_msa_msg_in_post(
        flask_test_client_msa_msg_in: FlaskClient,
        transaction_test_model: ModelTransaction,
        valid_xml: str,
    ) -> None:
        """
        Test the POST /msa/in endpoint with valid XML message
        Should return 200 status code
        """

        transaction: TypeTransaction = transaction_test_model.initiate()
        response: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": transaction.transaction_id,
                "Content-Type": "application/xml",
            },
            data=valid_xml,
        )

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 200
        assert data.get("status") == "OK"
        assert data.get("message") == "Request was received"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_invalid_xml_post(
        flask_test_client_msa_msg_in: FlaskClient,
        transaction_test_model: ModelTransaction,
        invalid_xml: str,
    ) -> None:
        """
        Test the POST /msa/in endpoint with invalid XML message
        Should return 400 status code
        """

        transaction: TypeTransaction = transaction_test_model.initiate()
        response: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": transaction.transaction_id,
                "Content-Type": "application/xml",
            },
            data=invalid_xml,
        )

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 400
        assert data.get("status") == "Rejected"
        assert data.get("message") == "Received an invalid XML message"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_missing_xml_post(
        flask_test_client_msa_msg_in: FlaskClient,
        transaction_test_model: ModelTransaction,
    ) -> None:
        """
        Test the POST /msa/in endpoint with missing XML message
        Should return 400 status code
        """

        transaction: TypeTransaction = transaction_test_model.initiate()
        response: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": transaction.transaction_id,
                "Content-Type": "application/xml",
            },
        )

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 400
        assert data.get("status") == "Rejected"
        assert data.get("message") == "Missing message body"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_missing_headers_post(
        flask_test_client_msa_msg_in: FlaskClient,
        # transaction_test_model: ModelTransaction,
        valid_xml: str,
    ) -> None:
        """
        Test the POST /msa/in endpoint with missing transaction id header
        Should return 400 status code
        """

        # Do not send the transaction id
        # request_id: str = os.environ.get("_FTL_REQUEST_ID")
        # transaction: TypeTransaction = transaction_test_model.initiate()
        response: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                # Do not send the transaction id
                # "X-Transaction-Id": transaction.transaction_id,
                "Content-Type": "application/xml",
            },
            data=valid_xml,
        )

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 400
        assert data.get("status") == "Rejected"
        assert data.get("message") == "Missing X-Transaction-Id HTTP header"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_not_initiated_transaction_post(
        flask_test_client_msa_msg_in: FlaskClient,
        # transaction_test_model: ModelTransaction,
        valid_xml: str,
    ) -> None:
        """
        Test the POST /msa/in endpoint with a transaction that was not initiated
        Should return 400 status code
        """

        # request_id: str = os.environ.get("_FTL_REQUEST_ID")
        # transaction: TypeTransaction = transaction_test_model.initiate()
        response: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": str(uuid.uuid4()),
                "Content-Type": "application/xml",
            },
            data=valid_xml,
        )

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 404
        assert data.get("status") == "Rejected"
        assert data.get("message") == "Could not find such transaction"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_processed_transaction_post(
        flask_test_client_msa_msg_in: FlaskClient,
        transaction_test_model: ModelTransaction,
        valid_xml: str,
    ) -> None:
        """
        Test the POST /msa/in endpoint with a transaction that was already processed
        Should return 400 status code
        """

        transaction: TypeTransaction = transaction_test_model.initiate()
        transaction_id: str = transaction.transaction_id

        transaction_test_model.receive(
            storage_path="N/A",
            message_type="N/A",
        )

        response: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": transaction_id,
                "Content-Type": "application/xml",
            },
            data=valid_xml,
        )

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 404
        assert data.get("status") == "Rejected"
        assert data.get("message") == "Could not find such transaction"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_same_invalid_transaction_post(
        flask_test_client_msa_msg_in: FlaskClient,
        valid_xml: str,
    ) -> None:
        """
        Test the POST /msa/in endpoint with a transaction that was already processed
        Should return 400 status code
        """

        transaction_id: str = str(uuid.uuid4())

        response_o: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": transaction_id,
                "Content-Type": "application/xml",
            },
            data=valid_xml,
        )
        response_s: TestResponse = flask_test_client_msa_msg_in.post(
            MSA_IN_URL,
            headers={
                "X-Transaction-Id": transaction_id,
                "Content-Type": "application/xml",
            },
            data=valid_xml,
        )

        data_o: Dict[str, Any] = json.loads(response_o.data)
        data_s: Dict[str, Any] = json.loads(response_s.data)

        assert response_o.status_code == 404
        assert data_o.get("status") == "Rejected"
        assert data_o.get("message") == "Could not find such transaction"
        assert data_o.get("request_id") == str(
            uuid.UUID(hex=data_o.get("request_id"), version=4)
        )

        assert response_s.status_code == 404
        assert data_s.get("status") == "Rejected"
        assert data_s.get("message") == "Could not find such transaction"
        assert data_s.get("request_id") == str(
            uuid.UUID(hex=data_s.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_trailing_slash_post(
        flask_test_client_msa_msg_in: FlaskClient,
    ) -> None:
        """
        Test the POST /msa/in/ endpoint
        Should return 404 status code
        """

        response: TestResponse = flask_test_client_msa_msg_in.post("/msa/in/")

        assert response.status_code == 404

    @staticmethod
    def test_msa_msg_in_healthy_get(flask_test_client_msa_msg_in: FlaskClient) -> None:
        """
        Test the GET /msa/in/_healthy endpoint
        Should return valid UUIDs and a healthy status
        """

        response: TestResponse = flask_test_client_msa_msg_in.get("/msa/in/_healthy")

        data: Dict[str, Any] = json.loads(response.data)

        assert response.status_code == 200
        assert data.get("status") == "OK"
        assert data.get("request_id") == str(
            uuid.UUID(hex=data.get("request_id"), version=4)
        )

    @staticmethod
    def test_msa_msg_in_healthy_trailing_slash_get(
        flask_test_client_msa_msg_in: FlaskClient,
    ) -> None:
        """
        Test the GET /msa/in/_healthy/ endpoint
        Should return 404 status code
        """

        response: TestResponse = flask_test_client_msa_msg_in.post("/msa/in/_healthy/")

        assert response.status_code == 404
