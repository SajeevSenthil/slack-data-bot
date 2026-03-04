import requests


def send_slack_response(response_url, message, with_button=False):

    if with_button:

        payload = {
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Export CSV"
                            },
                            "action_id": "export_csv",
                            "value": "export"
                        }
                    ]
                }
            ]
        }

    else:

        payload = {
            "response_type": "in_channel",
            "text": message
        }

    requests.post(response_url, json=payload)