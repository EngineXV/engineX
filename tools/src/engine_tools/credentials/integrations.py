"""Integration credential specs (CRM, messaging, calendar)."""

from .base import CredentialSpec

INTEGRATION_CREDENTIALS = {
    "hubspot": CredentialSpec(
        env_var="HUBSPOT_ACCESS_TOKEN",
        tools=["hubspot_search_contacts", "hubspot_create_contact"],
        node_types=["event_loop"],
        required=False,
        startup_required=False,
        help_url="https://developers.hubspot.com/docs/api/oauth-quickstart-guide",
        description="HubSpot CRM OAuth access for contact and deal workflows",
        engine_oauth_supported=True,
        engine_oauth_provider="hubspot",
        direct_api_key_supported=True,
        credential_id="hubspot",
        credential_key="access_token",
        api_key_instructions=(
            "Use OAuth Connect in the dashboard, or paste a private app access token."
        ),
    ),
    "zoho": CredentialSpec(
        env_var="ZOHO_ACCESS_TOKEN",
        tools=["zoho_search_records", "zoho_create_record"],
        node_types=["event_loop"],
        required=False,
        startup_required=False,
        help_url="https://www.zoho.com/crm/developer/docs/api/v2/oauth-overview.html",
        description="Zoho CRM OAuth access for record workflows",
        engine_oauth_supported=True,
        engine_oauth_provider="zoho",
        direct_api_key_supported=True,
        credential_id="zoho",
        credential_key="access_token",
    ),
    "slack": CredentialSpec(
        env_var="SLACK_BOT_TOKEN",
        tools=["slack_post_message", "slack_list_channels"],
        node_types=["event_loop"],
        required=False,
        startup_required=False,
        help_url="https://api.slack.com/apps",
        description="Slack bot token for alerts and channel messaging",
        credential_id="slack",
        credential_key="api_key",
        api_key_instructions=(
            "Create a Slack app, add bot scopes (chat:write, channels:read), install to workspace, "
            "copy the Bot User OAuth Token (xoxb-...)."
        ),
    ),
    "google_calendar": CredentialSpec(
        env_var="GOOGLE_CALENDAR_ACCESS_TOKEN",
        tools=[
            "calendar_check_availability",
            "calendar_create_event",
            "calendar_list_events",
        ],
        node_types=["event_loop"],
        required=False,
        startup_required=False,
        help_url="https://developers.google.com/calendar/api/guides/auth",
        description="Google Calendar OAuth for scheduling integrations",
        engine_oauth_supported=True,
        engine_oauth_provider="google_calendar",
        direct_api_key_supported=True,
        credential_id="google_calendar",
        credential_key="access_token",
        credential_group="google_workspace",
    ),
}
