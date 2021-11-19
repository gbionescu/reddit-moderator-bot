# API client library
import googleapiclient.discovery

# API information
api_service_name = "youtube"
api_version = "v3"
devkey = None

# API client
youtube = None

def get_channel_id(ytid):
    global youtube
    if not youtube:
        youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=devkey)

    # Request body
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=ytid
    )
    # Request execution
    response = request.execute()
    try:
        return response["items"][0]["snippet"]["channelId"]
    except Exception as e:
        print(response)