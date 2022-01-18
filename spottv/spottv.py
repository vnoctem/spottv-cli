import os
import logging
import json
import sys
import configparser

from pathlib import Path

import click
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc
)

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5

CONFIG_DIR = Path(click.get_app_dir("spottv"))
CONFIG_PATH = Path(CONFIG_DIR, "spottv.cfg")


class Assistant(object):
    """Sample Assistant that supports text based conversations.

    Args:
      language_code: language for the conversation.
      device_model_id: identifier of the device model.
      device_id: identifier of the registered device instance.
      display: enable visual display of assistant response.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, language_code, device_model_id, device_id,
                 channel, deadline_sec):
        self.language_code = language_code
        self.device_model_id = device_model_id
        self.device_id = device_id
        self.conversation_state = None
        # Force reset of first conversation.
        self.is_new_conversation = True
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(
            channel
        )
        self.deadline = deadline_sec

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False

    def assist(self, text_query):
        """Send a text request to the Assistant and playback the response.
        """

        #def iter_assist_requests():
        config = embedded_assistant_pb2.AssistConfig(
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=16000,
                volume_percentage=0,
            ),
            dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                language_code=self.language_code,
                conversation_state=self.conversation_state,
                is_new_conversation=self.is_new_conversation,
            ),
            device_config=embedded_assistant_pb2.DeviceConfig(
                device_id=self.device_id,
                device_model_id=self.device_model_id,
            ),
            text_query=text_query,
        )
        # Continue current conversation with later requests.
        self.is_new_conversation = False

        req = embedded_assistant_pb2.AssistRequest(config=config)
            # assistant_helpers.log_assist_request_without_audio(req)
            #yield req

        # text_response = None
        # html_response = None
        # for resp in self.assistant.Assist(iter_assist_requests(),
        #                                   self.deadline):
        #     # assistant_helpers.log_assist_response_without_audio(resp)
        #     if resp.screen_out.data:
        #         html_response = resp.screen_out.data
        #     if resp.dialog_state_out.conversation_state:
        #         conversation_state = resp.dialog_state_out.conversation_state
        #         self.conversation_state = conversation_state
        #     if resp.dialog_state_out.supplemental_display_text:
        #         text_response = resp.dialog_state_out.supplemental_display_text
        # return text_response, html_response


@click.group()
@click.option('--device-model-id',
              metavar='<device model id>',
              required=True,
              help=(('Unique device model identifier, '
                     'if not specified, it is read from --device-config')))
@click.option('--device-id',
              metavar='<device id>',
              required=True,
              help=(('Unique registered device instance identifier, '
                     'if not specified, it is read from --device-config, '
                     'if no device_config found: a new device is registered '
                     'using a unique id and a new device config is saved')))
@click.pass_context
def cli(ctx, device_model_id, device_id):
    ctx.obj['device_model_id'] = device_model_id
    ctx.obj['device_id'] = device_id


@cli.command()
@click.pass_obj
def launch(settings):
    send_text_query("open Spotify", settings['device_model_id'], settings['device_id'])


@cli.command()
@click.option('--api-endpoint', default=ASSISTANT_API_ENDPOINT,
              metavar='<api endpoint>', show_default=True,
              help='Address of Google Assistant API service.')
@click.option('--credentials',
              metavar='<credentials>', show_default=True,
              default=os.path.join(click.get_app_dir('google-oauthlib-tool'),
                                   'credentials.json'),
              help='Path to read OAuth2 credentials.')
@click.option('--lang', show_default=True,
              metavar='<language code>',
              default='en-US',
              help='Language code of the Assistant')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Verbose logging.')
@click.option('--grpc-deadline', default=DEFAULT_GRPC_DEADLINE,
              metavar='<grpc deadline>', show_default=True,
              help='gRPC deadline in seconds')
@click.pass_obj
def send(settings, api_endpoint, credentials, lang, verbose,
         grpc_deadline, *args, **kwargs):
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    # Load OAuth 2.0 credentials.
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None,
                                                                **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        return

    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request, api_endpoint)
    logging.info('Connecting to %s', api_endpoint)

    with Assistant(lang, settings['device_model_id'], settings['device_id'],
                   grpc_channel, grpc_deadline) as assistant:
        assistant.assist(text_query='open Spotify')


def send_text_query(text_query, device_model_id, device_id):
    credentials = os.path.join(click.get_app_dir('google-oauthlib-tool'),
                               'credentials.json')

    # Setup logging.
    logging.basicConfig(level=logging.DEBUG if True else logging.INFO)

    # Load OAuth 2.0 credentials.
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None,
                                                                **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        return

    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request, ASSISTANT_API_ENDPOINT)
    logging.info('Connecting to %s', ASSISTANT_API_ENDPOINT)

    with Assistant('en-US', device_model_id, device_id,
                   grpc_channel, DEFAULT_GRPC_DEADLINE) as assistant:
        assistant.assist(text_query=text_query)


def writeconfig(config):
    try:
        CONFIG_DIR.mkdir(parents=True)
    except FileExistsError:
        pass

    with CONFIG_PATH.open("w") as configfile:
        config.write(configfile)


def readconfig():
    config = configparser.ConfigParser()
    # ConfigParser.read does not take path-like objects <3.6.
    config.read(str(CONFIG_PATH))

    for req_section in "options":
        if req_section not in config.sections():
            config.add_section(req_section)
    return config


def get_config_as_dict():
    """
    Returns a dictionary of the form:
        {"options": {"key": "value"},
         "aliases": {"device1": "device_name"}}
    """

    config = readconfig()
    return {section: dict(config.items(section)) for section in config.sections()}


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
