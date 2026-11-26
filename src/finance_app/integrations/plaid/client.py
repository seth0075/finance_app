
import httpx

from finance_app.core.credentials import get_credential


class PlaidAPIError(Exception):

    def __init__(self, code, message, request_id=None):
        self.code = code
        self.request_id = request_id

        super().__init__(f"{code}: {message}")


class PlaidClient:

    def __init__(self, environment="sandbox"):
        if environment not in ("sandbox", "production"):
            raise ValueError("Invalid Plaid environment")

        self.environment = environment

        self.base_url = (
            f"https://{environment}.plaid.com"
        )

        self.client_id = get_credential(
            "plaid_client_id"
        )

        self.secret = get_credential(
            f"plaid_{environment}_secret"
        )

        if not self.client_id or not self.secret:
            raise RuntimeError(
                "Plaid credentials are not configured."
            )

    def request(
        self,
        endpoint: str,
        payload: dict
    ) -> dict:

        response = httpx.post(
            f"{self.base_url}{endpoint}",
            headers={
                "PLAID-CLIENT-ID": self.client_id,
                "PLAID-SECRET": self.secret,
                "Plaid-Version": "2020-09-14"
            },
            json=payload,
            timeout=60.0
        )

        from decimal import Decimal

        data = response.json(parse_float=Decimal)

        if response.is_error:
            raise PlaidAPIError(
                data.get("error_code", "UNKNOWN_ERROR"),
                data.get("error_message", "Request failed"),
                data.get("request_id")
            )

        return data

    def create_link_token(self) -> dict:
        return self.request(
            "/link/token/create",
            {
                "client_name": "Personal Dashboard",
                "language": "en",
                "country_codes": ["US"],
                "user": {
                    "client_user_id": "personal-dashboard-user"
                },
                "products": ["transactions"],
                "transactions": {
                    "days_requested": 730
                },
                "hosted_link": {}
            }
        )

    def get_link_session(self, link_token: str) -> dict:
        return self.request(
            "/link/token/get",
            {
                "link_token": link_token
            }
        )

    def exchange_public_token(
        self,
        public_token: str
    ) -> dict:

        return self.request(
            "/item/public_token/exchange",
            {
                "public_token": public_token
            }
        )

    def get_accounts(self, access_token: str) -> dict:
        return self.request(
            "/accounts/get",
            {
                "access_token": access_token
            }
        )

    def get_item(self, access_token: str) -> dict:
        return self.request(
            "/item/get",
            {
                "access_token": access_token
            }
        )

    def sync_transactions(
        self,
        access_token: str,
        cursor: str = ""
    ) -> dict:

        payload = {"access_token": access_token, "count": 500}
        if cursor:
            payload["cursor"] = cursor
        return self.request("/transactions/sync", payload)

    def remove_item(self, access_token: str) -> dict:
        return self.request(
            "/item/remove",
            {
                "access_token": access_token
            }
        )

    def create_sandbox_public_token(self) -> str:
        if self.environment != "sandbox":
            raise RuntimeError(
                "This method is only available in Sandbox."
            )

        response = self.request(
            "/sandbox/public_token/create",
            {
                "institution_id": "ins_109508",
                "initial_products": ["transactions"]
            }
        )

        return response["public_token"]
