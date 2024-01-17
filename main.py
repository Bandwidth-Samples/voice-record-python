import http
import os
import sys

import bandwidth
from bandwidth import ApiException
from bandwidth.models.bxml import Response as BxmlResponse
from bandwidth.models.bxml import SpeakSentence, PlayAudio, Record
from fastapi import FastAPI, Response
import uvicorn

try:
    BW_USERNAME = os.environ['BW_USERNAME']
    BW_PASSWORD = os.environ['BW_PASSWORD']
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_VOICE_APPLICATION_ID = os.environ['BW_VOICE_APPLICATION_ID']
    BW_NUMBER = os.environ['BW_NUMBER']
    USER_NUMBER = os.environ['USER_NUMBER']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
    BASE_CALLBACK_URL = os.environ['BASE_CALLBACK_URL']
except KeyError as e:
    print(f"Please set the environmental variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    username=BW_USERNAME,
    password=BW_PASSWORD
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_recordings_api_instance = bandwidth.RecordingsApi(bandwidth_api_client)


@app.get('/tone.mp3', status_code=http.HTTPStatus.OK)
def return_tone():
    return Response(content=open('Tone.mp3', 'rb').read(), media_type="audio/mpeg")


@app.post('/callbacks/callInitiatedCallback', status_code=http.HTTPStatus.OK)
def inbound_call(data: bandwidth.models.InitiateCallback):
    if data.event_type != "initiate":
        print(f"Received unexpected event type: {data.event_type}")
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)
    unavailable_speak_sentence = SpeakSentence(
        text="You have reached Vandelay Industries, Kal Varnsen is unavailable at this time."
    )
    message_speak_sentence = SpeakSentence(
        text="At the tone, please record your message, when you have finished recording, you may hang up."
    )
    tone = PlayAudio(audio_uri="/tone.mp3")
    record = Record(recording_available_url="/callbacks/recordingAvailableCallback", max_duration=30)
    bxml_response = BxmlResponse([unavailable_speak_sentence, message_speak_sentence, tone, record])

    return Response(content=bxml_response.to_bxml(), media_type="application/xml")


@app.post('/callbacks/recordingAvailableCallback', status_code=http.HTTPStatus.NO_CONTENT)
def outbound_call(data: bandwidth.models.RecordingAvailableCallback):
    if data.event_type != "recordingAvailable":
        print(f"Received unexpected event type: {data.event_type}")
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    file_format = data.file_format
    call_id = data.call_id
    recording_id = data.recording_id

    try:
        recording = bandwidth_recordings_api_instance.download_call_recording(BW_ACCOUNT_ID, call_id, recording_id)
    except ApiException as e:
        print(f"Error downloading recording: {e}")
        return Response(status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    with open(f"{recording_id}.{file_format}", "wb") as f:
        f.write(recording)


if __name__ == '__main__':
    uvicorn.run("main:app", port=LOCAL_PORT, reload=True)
