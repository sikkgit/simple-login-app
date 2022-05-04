import email
import random
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytest

from app.config import (
    ALERT_COMPLAINT_FORWARD_PHASE,
    ALERT_COMPLAINT_REPLY_PHASE,
    ALERT_COMPLAINT_TRANSACTIONAL_PHASE,
)
from app.db import Session
from app.email import headers
from app.handler.provider_complaint import (
    handle_hotmail_complaint,
    handle_yahoo_complaint,
)
from app.mail_sender import mail_sender
from app.models import Alias, ProviderComplaint, SentAlert, Mailbox
from tests.utils import create_new_user, create_random_email

origins = [
    [handle_yahoo_complaint, "yahoo", 6],
    [handle_hotmail_complaint, "hotmail", 3],
]


def prepare_complaint(message: Message, part_num: int) -> Message:
    complaint = MIMEMultipart("related")
    # When walking, part 0 is the full message so we -1, and we want to be part N so -1 again
    for i in range(part_num - 2):
        document = MIMEText("text", "plain")
        document.set_payload(f"Part {i}")
        complaint.attach(document)
    complaint.attach(message)

    return email.message_from_bytes(complaint.as_bytes())


@pytest.mark.parametrize("handle_ftor,provider,part_num", origins)
def test_provider_to_user(flask_client, handle_ftor, provider, part_num):
    user = create_new_user()
    original_message = Message()
    original_message[headers.TO] = user.email
    original_message[headers.FROM] = "nobody@nowhere.net"
    original_message.set_payload("Contents")

    complaint = prepare_complaint(original_message, part_num)
    assert handle_ftor(complaint)
    found = ProviderComplaint.filter_by(user_id=user.id).all()
    assert len(found) == 0
    alerts = SentAlert.filter_by(user_id=user.id).all()
    assert len(alerts) == 1
    assert alerts[0].alert_type == f"{ALERT_COMPLAINT_TRANSACTIONAL_PHASE}_{provider}"


@pytest.mark.parametrize("handle_ftor,provider,part_num", origins)
def test_provider_forward_phase(flask_client, handle_ftor, provider, part_num):
    user = create_new_user()
    alias = Alias.create_new_random(user)
    Session.commit()
    original_message = Message()
    original_message[headers.TO] = "nobody@nowhere.net"
    original_message[headers.FROM] = alias.email
    original_message.set_payload("Contents")

    complaint = prepare_complaint(original_message, part_num)
    assert handle_ftor(complaint)
    found = ProviderComplaint.filter_by(user_id=user.id).all()
    assert len(found) == 1
    alerts = SentAlert.filter_by(user_id=user.id).all()
    assert len(alerts) == 1
    assert alerts[0].alert_type == f"{ALERT_COMPLAINT_REPLY_PHASE}_{provider}"


@pytest.mark.parametrize("handle_ftor,provider,part_num", origins)
def test_provider_forward_phase_multiple_mailboxes(
    flask_client, handle_ftor, provider, part_num
):
    mail_sender.purge_stored_send_requests()
    user = create_new_user()
    email = create_random_email()
    mbox = Mailbox.create(user_id=user.id, email=email, verified=True, commit=True)
    alias = Alias.create(
        user_id=user.id, email=create_random_email(), mailbox_id=mbox.id, commit=True
    )
    Session.commit()
    original_message = Message()
    original_message[headers.TO] = "nobody@nowhere.net"
    original_message[headers.FROM] = alias.email
    original_message.set_payload("Contents")

    complaint = prepare_complaint(original_message, part_num)
    assert handle_ftor(complaint)
    found = ProviderComplaint.filter_by(user_id=user.id).all()
    assert len(found) == 1
    alerts = SentAlert.filter_by(user_id=user.id).all()
    assert len(alerts) == 1
    assert alerts[0].alert_type == f"{ALERT_COMPLAINT_REPLY_PHASE}_{provider}"
    send_requests = mail_sender.get_stored_send_requests()
    assert len(send_requests) == 1
    request = send_requests[0]
    assert email == request.envelope_to
    assert request.get_payload().find(email) > -1


@pytest.mark.parametrize("handle_ftor,provider,part_num", origins)
def test_provider_reply_phase(flask_client, handle_ftor, provider, part_num):
    user = create_new_user()
    alias = Alias.create_new_random(user)
    Session.commit()
    original_message = Message()
    original_message[headers.TO] = alias.email
    original_message[headers.FROM] = "no@no.no"
    original_message.set_payload("Contents")

    complaint = prepare_complaint(original_message, part_num)
    assert handle_ftor(complaint)
    found = ProviderComplaint.filter_by(user_id=user.id).all()
    assert len(found) == 0
    alerts = SentAlert.filter_by(user_id=user.id).all()
    assert len(alerts) == 1
    assert alerts[0].alert_type == f"{ALERT_COMPLAINT_FORWARD_PHASE}_{provider}"
