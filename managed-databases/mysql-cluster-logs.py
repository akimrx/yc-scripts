#!/usr/bin/env python3
# dont't forget install requirements: pip install requests

import json
import requests
import argparse

example = 'Example command: python3 mysql-cluster-logs.py --token {token} --cluster {id} ' + \
          '--service mysql-error --from-time "2020-05-10T22:00:00Z" --to-time "2020-05-10T23:00:00Z" '
parser = argparse.ArgumentParser(epilog=example)
commands = parser.add_argument_group('Commands')
commands.add_argument('--token', metavar='IAM', type=str, help='IAM-token')
commands.add_argument('--cluster', metavar='id', type=str, help='Cluster ID')
commands.add_argument('--service', metavar='type', type=str, help='Service: MYSQL_ERROR / MYSQL_GENERAL / MYSQL_SLOW_QUERY / MYSQL_AUDIT')
commands.add_argument('--from-time', metavar='time', type=str, help='like a 2020-05-05T00:00:00Z')
commands.add_argument('--to-time', metavar='time', type=str, help='like a 2020-05-05T00:00:00Z')
commands.add_argument('--json', action='store_true', default=False, help='save logs as json file')
args = parser.parse_args()


def pretty_format(message: str):
    """Usual log formatting."""
    useful_data = message.get('message')
    if useful_data.get('command') is None and useful_data.get('message') is None:
        result = f'{message.get("timestamp")} - {useful_data}'
    elif useful_data.get('command') is None:
        result = f'{message.get("timestamp")} - {useful_data.get("hostname")} - ' + \
                 f'{useful_data.get("status")} - {useful_data.get("message")}'
    else:
        result = f'{message.get("timestamp")} - {useful_data.get("hostname")} ' + \
                 f'- {useful_data.get("command")} - {useful_data.get("argument")}'
    return result


def list_logs(token: str, cluster_id: str, service='MYSQL_GENERAL'):
    """Collects all logs from the API for the specified time period."""
    service = service.replace('-', '_')
    url = f'https://mdb.api.cloud.yandex.net/managed-mysql/v1/clusters/' + \
          f'{cluster_id}:logs?pageSize=1000&serviceType={service.upper()}'
    headers = {'Authorization': f'Bearer {token}'}

    if args.from_time:
        url += f'&fromTime={args.from_time}'

    if args.to_time:
        url += f'&toTime={args.to_time}'

    messages = list()
    page_token = None
    running = True

    while running:
        if page_token is not None:
            url += f'&pageToken={page_token}'

        r = requests.get(url, headers=headers)
        r.raise_for_status()
        response = r.json()

        for message in response.get('logs', []):
            messages.append(message) if args.json else messages.append(pretty_format(message))

        page_token = response.get('nextPageToken', None)
        running = False if page_token is None else True

    return messages


def save_to_file(data: list, format='pretty'):
    """Save logs from API to file."""
    if format == 'json':
        filename = 'mysql.json'
        with open(filename, 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=2, ensure_ascii=False)
    else:
        filename = 'mysql.log'
        with open(filename, 'w') as outfile:
            for line in data:
                outfile.write(f'{line}\n')
    outfile.close()
    print(f'Logs saved to file "{filename}"')


if __name__ == '__main__':
    token = args.token
    cluster = args.cluster
    service = args.service or 'MYSQL_GENERAL'

    if not args.token or not args.cluster:
        raise ValueError('cluster and token is required, use --help for details')

    try:
        logs = list_logs(token=token, cluster_id=cluster, service=service)
        save_to_file(logs, format='json') if args.json else save_to_file(logs)
    except requests.exceptions.HTTPError as err:
        print(err)
