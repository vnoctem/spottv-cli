import json
import logging
import os

import click
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from assistant import Assistant

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5

SCOPE = 'user-read-playback-state user-modify-playback-state'


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
def on(settings):
    """
    Turn on TV and launch Spotify app
    """
    send_text_query('open Spotify', settings['device_model_id'], settings['device_id'])
    play(spotify_uri='')


@cli.command()
@click.pass_obj
def off(settings):
    """
    Turn off TV
    """
    send_text_query('turn off TV', settings['device_model_id'], settings['device_id'])


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


def play(spotify_uri):
    spotify_controller = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
    devices = spotify_controller.devices()
    chromecast = None

    if not devices:
        click.echo('No device found')
    else:
        for device in devices['devices']:
            if device['type'] == 'TV':
                chromecast = device
                break

        if not chromecast:
            click.echo('No Chromecast found')
        else:
            chromecast_id = chromecast['id']
            chromecast_name = chromecast['name']

            playlist = spotify_controller.playlist('37i9dQZF1DXdxcBWuJkbcy')
            playlist_name = playlist['name']

            click.echo(f"Starting playback of '{playlist_name}' on {chromecast_name}...")
            # spotify_controller.shuffle(True, chromecast_id)
            spotify_controller.start_playback(device_id=chromecast_id,
                                              context_uri='https://open.spotify.com/playlist/37i9dQZF1DXdxcBWuJkbcy')


def send_text_query(text_query, device_model_id, device_id):
    """Send a text query to specified device

     Args:
      text_query (str): text query to send (equivalent of a typed voice command).
      device_model_id (str): identifier of the device model.
      device_id (str): identifier of the registered device instance.
    """

    credentials = os.path.join(click.get_app_dir('google-oauthlib-tool'), 'credentials.json')

    # Setup logging.
    # logging.basicConfig(level=logging.DEBUG if True else logging.INFO)

    # Load OAuth 2.0 credentials.
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None, **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        return

    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials,
        http_request,
        ASSISTANT_API_ENDPOINT
    )

    logging.info('Connecting to %s', ASSISTANT_API_ENDPOINT)

    # Call Assistant
    with Assistant('en-US',
                   device_model_id,
                   device_id,
                   grpc_channel,
                   DEFAULT_GRPC_DEADLINE
                   ) as assistant:
        assistant.assist(text_query=text_query)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
