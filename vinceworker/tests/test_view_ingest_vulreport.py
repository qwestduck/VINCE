import json

from typing import Literal
from unittest import mock

from django.contrib.auth.models import User

from vince.models import BounceEmailNotification, FollowUp, Ticket, TicketQueue
from vinceworker.tests import StructureMatchedViewTestCase

class TestIngestVulreport(StructureMatchedViewTestCase):
    databases = ["default", "vincecomm"]

    url = "/vinceworker/ingest-vulreport/"
    content_type = "application/json"


class TestUpdateSrmailPattern(TestIngestVulreport):
    def fill_pattern(self, _=""):
        return {"Message": _, "MessageAttributes": {"MessageType": {"Value": "UpdateSrmail"}}}

    @mock.patch("boto3.client", mock.Mock())
    def test_update_srmail_responds_success(self):
        response = self.post()

        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.content, b'{"response": "success"}')
        self.assertEqual(response.status_code, 200)


class TestBounceNotificationPattern(TestIngestVulreport):
    def fill_pattern(self, froms, headers, bounced_recipients, bounce_type, notification_type: Literal["Bounce", "Complaint"] = "Bounce"):
        return {
            "Message": json.dumps(
                {
                    "notificationType": notification_type,
                    "mail": {"commonHeaders": {"from": [*froms], **headers}},
                    "bounce": {"bouncedRecipients": [*bounced_recipients], "bounceType": bounce_type}
                }
            )
        }

    def test_bounce_ticket_when_all_recipients_inactive(self):
        # Build state
        User(username="deactivated_user@example.com", is_active=False).save()

        # Assert initial state
        self.assertEqual(Ticket.objects.all().count(), 0)
        self.assertEqual(FollowUp.objects.all().count(), 0)

        # Request
        response = self.post(
            # Shape request
            froms = ["mock_from", "mock_from"],
            headers = {},
            bounced_recipients = ["deactivated_user@example.com"],
            bounce_type="Permanent"
        )

        # Assert final state
        self.assertEqual(Ticket.objects.all().count(), 0)
        self.assertEqual(FollowUp.objects.all().count(), 0)

        # Assert response
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.content, b'{"response": "success"}')
        self.assertEqual(response.status_code, 200)

    def test_bounce_ticket_when_one_recipient_active_permanent_bounce(self):
        User(username="activated_user@example.com", is_active=True).save()
        TicketQueue(title="General").save()

        self.assertEqual(Ticket.objects.all().count(), 0)
        self.assertEqual(FollowUp.objects.all().count(), 0)
        self.assertEqual(BounceEmailNotification.objects.all().count(), 0)

        response = self.post(
            froms = ["mock_from", "mock_from"],
            headers = {},
            bounced_recipients = ["activated_user@example.com"],
            bounce_type="Permanent"
        )

        self.assertEqual(Ticket.objects.all().count(), 1)
        self.assertEqual(FollowUp.objects.all().count(), 1)
        self.assertEqual(BounceEmailNotification.objects.all().count(), 1)

        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.content, b'{"response": "success"}')
        self.assertEqual(response.status_code, 200)

    @mock.patch('vince.lib.VINCE_IGNORE_TRANSIENT_BOUNCES', True)
    def test_bounce_ticket_when_one_recipient_active_transient_bounce(self):
        """
        If VINCE_IGNORE_TRANSIENT_BOUNCES is set to True, VINCE will only
        create a ticket for PERMANENT bounces. Transient bounces will be
        recorded and can be viewed in the Bounce Manager, but a ticket will
        not be created.
        """
        User(username="activated_user@example.com", is_active=True).save()

        self.assertEqual(Ticket.objects.all().count(), 0)
        self.assertEqual(FollowUp.objects.all().count(), 0)
        self.assertEqual(BounceEmailNotification.objects.all().count(), 0)

        response = self.post(
            froms = ["mock_from", "mock_from"],
            headers = {},
            bounced_recipients = ["activated_user@example.com"],
            bounce_type="Transient"
        )

        self.assertEqual(Ticket.objects.all().count(), 0)
        self.assertEqual(FollowUp.objects.all().count(), 0)
        self.assertEqual(BounceEmailNotification.objects.all().count(), 1)

        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.content, b'{"response": "success"}')
        self.assertEqual(response.status_code, 200)
