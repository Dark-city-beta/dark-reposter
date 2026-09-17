from __future__ import annotations

import asyncio
import os

import httpx
from dotenv import load_dotenv


ENDPOINT = "https://api.buffer.com"


async def main() -> None:
    load_dotenv()
    api_key = os.getenv("BUFFER_API_KEY", "").strip()
    org_id = os.getenv("BUFFER_ORGANIZATION_ID", "").strip()
    if not api_key:
        raise SystemExit("Set BUFFER_API_KEY in .env first")

    async with httpx.AsyncClient(timeout=30) as client:
        if not org_id:
            account_query = """
            query Account {
              account {
                id
                organizations {
                  id
                  name
                }
              }
            }
            """
            account = await graphql(client, api_key, account_query)
            print("Organizations:")
            for org in account["data"]["account"]["organizations"]:
                print(f"  {org['id']}  {org['name']}")
            print("\nPut one id into BUFFER_ORGANIZATION_ID and run again.")
            return

        channels_query = """
        query GetChannels($organizationId: OrganizationId!) {
          channels(input: { organizationId: $organizationId }) {
            id
            name
            displayName
            service
            isQueuePaused
          }
        }
        """
        data = await graphql(client, api_key, channels_query, {"organizationId": org_id})
        print("Channels:")
        for channel in data["data"]["channels"]:
            print(
                f"  {channel['service']:<10} {channel['id']}  "
                f"{channel.get('displayName') or channel.get('name')}"
            )


async def graphql(client: httpx.AsyncClient, api_key: str, query: str, variables=None):
    response = await client.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        raise SystemExit(data["errors"])
    return data


if __name__ == "__main__":
    asyncio.run(main())
