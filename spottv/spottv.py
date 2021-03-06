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
@click.pass_context
def spottv(ctx):
    return


@spottv.command()
@click.pass_obj
def on(settings):
    """
    Turn on TV and launch Spotify app
    """
    send_text_query('turn on Google TV', settings['device_model_id'], settings['device_id'])
    # play_spotify_uri(spotify_uri='')


@spottv.command()
@click.pass_obj
def off(settings):
    """
    Turn off TV
    """
    send_text_query('turn off TV', settings['device_model_id'], settings['device_id'])


@spottv.command()
@click.argument('playlist_name')
@click.pass_obj
def play(settings, playlist_name):
    """
    Play a playlist defined in config.json
    Args:
        settings: Device info
        playlist_name: Name of the playlist
    """
    file = open('config.json')
    config_data = json.load(file)
    spotify_uri = config_data['playlists'][playlist_name]
    file.close()

    send_text_query('turn on Google TV', settings['device_model_id'], settings['device_id'])
    play_spotify_uri(spotify_uri)


def play_spotify_uri(spotify_uri):
    """
    Start playback of Spotify URI
    Args:
        spotify_uri (str): URI of Spotify track, album or playlist
    """
    spotify_controller = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))

    devices = spotify_controller.devices()
    chromecast = None

    if not devices:
        click.echo('No device found')
    else:
        # click.echo(devices)
        for device in devices['devices']:
            if device['type'] == 'TV':
                chromecast = device
                break

        if not chromecast:
            click.echo('No Chromecast found')
        else:
            chromecast_id = chromecast['id']
            chromecast_name = chromecast['name']

            playlist = spotify_controller.playlist(spotify_uri)
            playlist_name = playlist['name']

            click.echo(f"Starting playback of '{playlist_name}' on {chromecast_name}...")
            # spotify_controller.shuffle(True, chromecast_id)
            spotify_controller.start_playback(device_id=chromecast_id, context_uri=spotify_uri)


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
        logging.error('google-oauthlib-tool '
                      '--client-secrets client_secret_811734406476-tvp38peele577b6dfv7roigsdf727tog.apps'
                      '.googleusercontent.com.json '
                      '--scope https://www.googleapis.com/auth/assistant-sdk-prototype '
                      '--save --headless')
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


def get_device_info():
    device_info = {}

    file = open('device_model.json')
    model_data = json.load(file)
    device_info['device_model_id'] = model_data['device_model_id']
    file.close()

    file = open('device_instance.json')
    instance_data = json.load(file)
    device_info['device_id'] = instance_data['id']
    file.close()

    return device_info


def main():
    return spottv(obj=get_device_info())


if __name__ == '__main__':
    main()
