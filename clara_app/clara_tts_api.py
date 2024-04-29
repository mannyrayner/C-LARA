"""
clara_tts_api.py

This module implements text-to-speech (TTS) functionality for various engines, including ReadSpeaker, Google TTS, and ABAIR.

Classes:
- TTSEngine: Base class for TTS engines.
- ReadSpeakerEngine: Derived class for ReadSpeaker TTS engine.
- GoogleTTSEngine: Derived class for Google TTS engine.
- ABAIREngine: Derived class for ABAIR TTS engine.
- IPAReaderEngine: Derived class for ipa-reader phonetic TTS engine.

Functions:
- create_tts_engine(engine_type: str) -> TTSEngine:
Returns an instance of the specified TTS engine type.
- get_tts_engine(language: str) -> Optional[TTSEngine]:
Returns the first available TTS engine that supports the given language.
- get_default_voice(language: str, tts_engine: Optional[TTSEngine]=None) -> Optional[str]:
Returns the default voice for the given language in the specified TTS engine or the first available engine if not specified.
- get_language_id(language: str, tts_engine: Optional[TTSEngine]=None) -> Optional[str]:
Returns the language ID for the given language in the specified TTS engine or the first available engine if not specified.
"""

from .clara_utils import get_config, post_task_update, os_environ_or_none
from .clara_utils import absolute_file_name, absolute_local_file_name, local_file_exists, write_local_txt_file

from openai import OpenAI
from google.cloud import texttospeech

import os
import tempfile
import requests
import base64
import gtts
import traceback
import json

config = get_config()

class TTSEngine:
    def create_mp3(self, language_id, voice_id, text, output_file):
        raise NotImplementedError

class ReadSpeakerEngine(TTSEngine):
    def __init__(self, api_key=None, base_url=None):
        self.tts_engine_type = 'readspeaker'
        self.phonetic = False
        self.api_key = api_key or self.load_api_key()
        self.base_url = base_url or config.get('tts', 'readspeaker_base_url')
        self.languages = { 'english':
                            {  'language_id': 'en_uk',
                               'voices': [ 'Alice-DNN' ]
                               },
                            'french':
                            {  'language_id': 'fr_fr',
                               'voices': [ 'Elise-DNN' ]
                               },
                            'italian':
                            {  'language_id': 'it_it',
                               'voices': [ 'Gina-DNN' ]
                               },
                            'german':
                            {  'language_id': 'de_de',
                               'voices': [ 'Max-DNN' ]
                               },
                            'danish':
                            {  'language_id': 'da_dk',
                               'voices': [ 'Lene' ]
                               },
                            'spanish':
                            {  'language_id': 'es_es',
                               'voices': [ 'Pilar-DNN' ]
                               },
                            'icelandic':
                            {  'language_id': 'is_is',
                               'voices': [ 'Female01' ]
                               },
                            'swedish':
                            {  'language_id': 'sv_se',
                               'voices': [ 'Maja-DNN' ]
                               },
                            'farsi':
                            {  'language_id': 'fa_ir',
                               'voices': [ 'Female01' ]
                               },
                            'mandarin':
                            {  'language_id': 'zh_cn',
                               'voices': [ 'Hui' ]
                               },
                            'dutch':
                            {  'language_id': 'nl_nl',
                               'voices': [ 'Ilse-DNN' ]
                               },
                            'japanese':
                            {  'language_id': 'ja_jp',
                               'voices': [ 'Sayaka-DNN' ]
                               },
                            'polish':
                            {  'language_id': 'pl_pl',
                               'voices': [ 'Aneta-DNN' ]
                               },
                            'slovak':
                            {  'language_id': 'sk_sk',
                               'voices': [ 'Jakub' ]
                               }
                          }


    def load_api_key(self):
        try:
            key_path = absolute_local_file_name(config.get('paths', 'readspeaker_license_key'))
            with open(key_path, 'r') as f:
                return f.read().strip()
        except:
            return None
        
    def create_mp3(self, language_id, voice_id, text, output_file, callback=None):
        data = {
            "key": self.api_key,
            "lang": language_id,
            "voice": voice_id,
            "text": text,
            "streaming": 0
        }
        response = requests.post(self.base_url, data, stream=True)
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            return False

class GoogleTTSEngine(TTSEngine):
    def __init__(self):
        self.tts_engine_type = 'google'
        self.phonetic = False
        self.languages =  {'afrikaans': {'language_id': 'af-ZA', 'voices': ['default']},
                           #'albanian': {'language_id': 'sq', 'voices': ['default']},
                           'arabic': {'language_id': 'ar-XA', 'voices': ['ar-XA-Wavenet-B', 'default']},
                           'american english': {'language_id': 'en-US', 'voices': ['en-US-Neural2-A', 'default']},
                           'australian english': {'language_id': 'en-AU', 'voices': ['en-AU-Neural2-D', 'default']},
                           #'armenian': {'language_id': 'hy', 'voices': ['default']},
                           'basque': {'language_id': 'eu-ES', 'voices': ['default']},
                           'bengali': {'language_id': 'bn-IN', 'voices': ['bn-IN-Wavenet-B', 'default']},
                           #'bosnian': {'language_id': 'bs', 'voices': ['default']},
                           'catalan': {'language_id': 'ca-ES', 'voices': ['default']},
                           'cantonese': {'language_id': 'yue-HK', 'voices': ['yue-HK-Standard-D', 'default']},
                           'chinese': {'language_id': 'cmn-CN', 'voices': ['cmn-CN-Wavenet-C', 'default']},
                           'mandarin': {'language_id': 'cmn-CN', 'voices': ['cmn-CN-Wavenet-C', 'default']},
                           'taiwanese': {'language_id': 'cmn-TW', 'voices': ['cmn-TW-Wavenet-B', 'default']},
                           #'croatian': {'language_id': 'hr', 'voices': ['default']},
                           'czech': {'language_id': 'cs-CZ', 'voices': ['cs-CZ-Wavenet-A', 'default']},
                           'danish': {'language_id': 'da-DK', 'voices': ['da-DK-Neural2-D', 'default']},
                           'dutch': {'language_id': 'nl-NL', 'voices': ['nl-NL-Wavenet-C', 'default']},
                           'english': {'language_id': 'en-GB', 'voices': ['en-GB-News-J', 'default']},
                           #'esperanto': {'language_id': 'eo', 'voices': ['default']},
                           #'estonian': {'language_id': 'et', 'voices': ['default']},
                           'filipino': {'language_id': 'fil-PH', 'voices': ['fil-PH-Wavenet-C', 'default']},
                           'finnish': {'language_id': 'fi-FI', 'voices': ['i-FI-Wavenet-A', 'default']},
                           'french': {'language_id': 'fr-FR', 'voices': ['fr-FR-Studio-D', 'default']},
                           'galician': {'language_id': 'gl-ES', 'voices': ['default']},
                           'german': {'language_id': 'de-DE', 'voices': ['de-DE-Studio-B', 'default']},
                           'greek': {'language_id': 'el-GR', 'voices': ['el-GR-Wavenet-A', 'default']},
                           'gujarati': {'language_id': 'gu-IN', 'voices': ['gu-IN-Wavenet-B', 'default']},
                           'hebrew': {'language_id': 'he-IL', 'voices': ['he-IL-Wavenet-B', 'default']},
                           'hindi': {'language_id': 'hi-IN', 'voices': ['hi-IN-Wavenet-B', 'default']},
                           'hungarian': {'language_id': 'hu-HU', 'voices': ['hu-HU-Wavenet-A', 'default']},
                           'icelandic': {'language_id': 'is-IS', 'voices': ['default']},
                           'indonesian': {'language_id': 'id-ID', 'voices': ['id-ID-Wavenet-B', 'default']},
                           'italian': {'language_id': 'it-IT', 'voices': ['it-IT-Wavenet-D', 'default']},
                           'japanese': {'language_id': 'ja-JP', 'voices': ['ja-JP-Neural2-C', 'default']},
                           #'javanese': {'language_id': 'jw', 'voices': ['default']},
                           'kannada': {'language_id': 'kn-IN', 'voices': ['kn-IN-Wavenet-B', 'default']},
                           #'khmer': {'language_id': 'km', 'voices': ['default']},
                           'korean': {'language_id': 'ko-KR', 'voices': ['ko-KR-Neural2-C', 'default']},
                           #'latin': {'language_id': 'la', 'voices': ['default']},
                           'latvian': {'language_id': 'lv-LV', 'voices': ['default']},
                           'lithuanian': {'language_id': 'lt-LT', 'voices': ['default']},
                           #'macedonian': {'language_id': 'mk', 'voices': ['default']},
                           'malay': {'language_id': 'ms-MY', 'voices': ['ms-MY-Standard-D', 'default']},
                           'malayalam': {'language_id': 'ml-IN', 'voices': ['ml-IN-Wavenet-B', 'default']},
                           'marathi': {'language_id': 'mr-IN', 'voices': ['mr-IN-Wavenet-B', 'default']},
                           #'burmese': {'language_id': 'my', 'voices': ['default']},
                           #'nepali': {'language_id': 'ne', 'voices': ['default']},
                           'norwegian': {'language_id': 'nb-NO', 'voices': ['nb-NO-Wavenet-B', 'default']},
                           'polish': {'language_id': 'pl-PL', 'voices': ['pl-PL-Standard-B', 'default']},
                           'portuguese': {'language_id': 'pt-PT', 'voices': ['pt-PT-Wavenet-B', 'default']},
                           'punjabi': {'language_id': 'pa-IN', 'voices': ['pa-IN-Wavenet-B', 'default']},
                           'romanian': {'language_id': 'ro-RO', 'voices': ['ro-RO-Wavenet-A', 'default']},
                           'russian': {'language_id': 'ru-RU', 'voices': ['ru-RU-Standard-D', 'default']},
                           'serbian': {'language_id': 'sr-RS', 'voices': ['default']},
                           #'sinhala': {'language_id': 'si', 'voices': ['default']},
                           'slovak': {'language_id': 'sk-SK', 'voices': ['sk-SK-Wavenet-A', 'default']},
                           'spanish': {'language_id': 'es-ES', 'voices': ['es-ES-Neural2-F', 'default']},
                           #'sundanese': {'language_id': 'su', 'voices': ['default']},
                           #'swahili': {'language_id': 'sw', 'voices': ['default']},
                           'swedish': {'language_id': 'sv-SE', 'voices': ['sv-SE-Wavenet-C', 'default']},
                           'tamil': {'language_id': 'ta-IN', 'voices': ['ta-IN-Wavenet-B', 'default']},
                           'telugu': {'language_id': 'te-IN', 'voices': ['default']},
                           'thai': {'language_id': 'th-TH', 'voices': ['th-TH-Neural2-C', 'default']},
                           'turkish': {'language_id': 'tr-TR', 'voices': ['tr-TR-Wavenet-B', 'default']},
                           'ukrainian': {'language_id': 'uk-UA', 'voices': ['uk-UA-Wavenet-A', 'default']},
                           #'urdu': {'language_id': 'ur', 'voices': ['default']},
                           'vietnamese': {'language_id': 'vi-VN', 'voices': ['vi-VN-Wavenet-B', 'default']},
                           #'welsh': {'language_id': 'cy', 'voices': ['default']}
                        }

    def create_mp3(self, language_id, voice_id, text, output_file, callback=None):
        #return self.create_mp3_gtts(language_id, voice_id, text, output_file, callback=callback)
        return self.create_mp3_google_cloud(language_id, voice_id, text, output_file, callback=callback)

    def create_mp3_google_cloud(self, language_id, voice_id, text, output_file, callback=None):
        try:
            found_google_creds = self._load_google_application_creds(callback=callback)

            if found_google_creds:
                # Initialize the client
                client = texttospeech.TextToSpeechClient()

                # Set the text input
                synthesis_input = texttospeech.SynthesisInput(text=text)

                # Specify the voice, if possible using its name
                if voice_id == 'default':
                    voice = texttospeech.VoiceSelectionParams(
                        language_code=language_id
                        )
                else:
                    voice = texttospeech.VoiceSelectionParams(
                        language_code=language_id,
                        name=voice_id
                        )

                # Specify the audio configuration 
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                )

                # Perform the Text-to-Speech request
                response = client.synthesize_speech(
                    input=synthesis_input, 
                    voice=voice, 
                    audio_config=audio_config
                    )

                # Save the audio to the file
                with open(output_file, "wb") as out:
                    out.write(response.audio_content)
                return True
            
        except requests.exceptions.RequestException as e:
            post_task_update(callback, f"*** Warning: Network error while creating Google TTS mp3 for '{text}': {str(e)}")
            return False
        except IOError as e:
            post_task_update(callback, f"*** Warning: IOError while saving Google TTS mp3 for '{text}': {str(e)}")
            return False
        except Exception as e:
            post_task_update(callback, f"*** Warning: unable to create Google TTS mp3 for '{text}': {str(e)}")
            return False

    def create_mp3_gtts(self, language_id, voice_id, text, output_file, callback=None):
        try:
            found_google_creds = self._load_google_application_creds(callback=callback)

            if found_google_creds:
                tts = gtts.gTTS(text, lang=language_id)
                tts.save(output_file)
                return True
##        except gtts.GTTSError as e:
##            post_task_update(callback, f"*** Warning: gTTS error while creating Google TTS mp3 for '{text}': {str(e)}")
##            return False
        except requests.exceptions.RequestException as e:
            post_task_update(callback, f"*** Warning: Network error while creating Google TTS mp3 for '{text}': {str(e)}")
            return False
        except IOError as e:
            post_task_update(callback, f"*** Warning: IOError while saving Google TTS mp3 for '{text}': {str(e)}")
            return False
        except Exception as e:
            post_task_update(callback, f"*** Warning: unable to create Google TTS mp3 for '{text}': {str(e)}")
            return False

    def _load_google_application_creds(self, callback=None):
        creds_file = os_environ_or_none('GOOGLE_APPLICATION_CREDENTIALS')
        creds_string = os_environ_or_none('GOOGLE_CREDENTIALS_JSON')
        
        if creds_file and local_file_exists(creds_file):
            return True
        elif creds_string:
            creds_file = '/tmp/google_credentials_from_env.json'
            write_local_txt_file(creds_string, creds_file)                
            # Set the environment variable so gTTS can pick it up
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_file
            return True 
        else:
            post_task_update(callback, f"*** Warning: unable to find Google credentials in GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_CREDENTIALS_JSON")
            return False

class OpenAITTSEngine(TTSEngine):
    def __init__(self):
        self.tts_engine_type = 'openai'
        self.open_ai_key = os.environ["OPENAI_API_KEY"]
        self.phonetic = False
        self._openai_supported_languages = ['afrikaans', 'arabic', 'armenian', 'azerbaijani', 'belarusian',
                                            'bosnian', 'bulgarian', 'catalan', 'chinese', 'croatian', 'czech',
                                            'danish', 'dutch', 'english', 'estonian', 'finnish', 'french',
                                            'galician', 'german', 'greek', 'hebrew', 'hindi', 'hungarian',
                                            'icelandic', 'indonesian', 'italian', 'japanese', 'kannada', 'kazakh',
                                            'korean', 'latvian', 'lithuanian', 'macedonian', 'malay', 'marathi',
                                            'māori', 'nepali', 'norwegian', 'persian', 'polish', 'portuguese',
                                            'romanian', 'russian', 'serbian', 'slovak', 'slovenian', 'spanish',
                                            'swahili', 'swedish', 'tagalog', 'tamil', 'thai', 'turkish', 'ukrainian',
                                            'urdu', 'vietnamese', 'welsh']
        self._openai_supported_voices = ['onyx', 'alloy', 'echo', 'fable', 'nova', 'shimmer']
                                            
        self.languages =  { language: {'language_id': language, 'voices': self._openai_supported_voices }
                            for language in self._openai_supported_languages }
                           
    def create_mp3(self, language_id, voice_id, text, output_file, callback=None):
        try: 
            client = OpenAI(api_key=self.open_ai_key)
            speech_file_path = absolute_local_file_name(output_file)
            response = client.audio.speech.create(
                              model="tts-1",
                              voice=voice_id,
                              input=text
                              )
            response.stream_to_file(speech_file_path)
            return True
        
        except requests.exceptions.RequestException as e:
            post_task_update(callback, f"*** Warning: Network error while creating OpenAI TTS mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        except IOError as e:
            post_task_update(callback, f"*** Warning: IOError while saving OpenAI TTS mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        except Exception as e:
            post_task_update(callback, f"*** Warning: unable to create OpenAI TTS mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False

class ABAIREngine(TTSEngine):
    def __init__(self, base_url=None):
        self.tts_engine_type = 'abair'
        self.phonetic = False
        self.base_url = base_url or config.get('tts', 'abair_base_url')
        self.languages = { 'irish':
                            {  'language_id': 'ga-IE',
                               'voices': [
                                   'ga_UL_anb_nemo',
                                   'ga_UL_anb_exthts',
                                   'ga_UL_anb_piper',
                                   'ga_CO_snc_nemo',
                                   'ga_CO_snc_exthts',
                                   'ga_CO_snc_piper',
                                   'ga_CO_pmc_exthts',
                                   'ga_CO_pmc_nemo',
                                   'ga_MU_nnc_nemo',
                                   'ga_MU_nnc_exthts',
                                   'ga_MU_dms_nemo',
                                   'ga_MU_dms_piper',
                               ]
                            }
                          }

    def create_mp3(self, language_id, voice_id, text, output_file, callback=None):
        data = {
            "synthinput": {
                "text": text
            },
            "voiceparams": {
                "languageCode": language_id,
                "name": voice_id
            },
            "audioconfig": {
                "audioEncoding": "MP3"
            }
        }
        response = requests.post(self.base_url, json=data)
        if response.status_code == 200:
            encoded_audio = response.json()["audioContent"]
            decoded_audio = base64.b64decode(encoded_audio)
            with open(output_file, 'wb') as f:
                f.write(decoded_audio)
            return True
        else:
            return False

class ElevenLabsEngine(TTSEngine):
    def __init__(self, base_url=None):
        self.tts_engine_type = 'eleven_labs'
        self.phonetic = False
        self.base_url = base_url
        self.languages = { 'romanian':
                           {  'language_id': 'ro-RO',
                               'voices': [
                                   'XS5fYqdP9mR1As3yhU5V',
                               ]
                            }
                          }

    def get_voices(self):
        url = "https://api.elevenlabs.io/v1/voices"

        headers = {
            "Accept": "application/json",
            "xi-api-key": os.environ["ELEVEN_LABS_API_KEY"],
            "Content-Type": "application/json"
            }

        response = requests.get(url, headers=headers)
        
        data = response.json()

        return data['voices']

    # Code slightly adapted from https://elevenlabs.io/docs/api-reference/getting-started
    def create_mp3(self, language_id, voice_id, text, output_file, callback=None):
        try:
            CHUNK_SIZE = 1024  # Size of chunks to read/write at a time
            XI_API_KEY = os.environ["ELEVEN_LABS_API_KEY"]
            VOICE_ID = voice_id  # ID of the voice model to use
            TEXT_TO_SPEAK = text  # Text you want to convert to speech
            OUTPUT_PATH = absolute_local_file_name(output_file)  # Path to save the output audio file

            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"

            # Set up headers for the API request, including the API key for authentication
            headers = {
                "Accept": "application/json",
                "xi-api-key": XI_API_KEY
            }

            # Set up the data payload for the API request, including the text and voice settings
            data = {
                "text": TEXT_TO_SPEAK,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }

            response = requests.post(tts_url, headers=headers, json=data, stream=True)

            if response.ok:
                with open(OUTPUT_PATH, "wb") as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                return True
            else:
                print(response.text)
                return False
        except requests.exceptions.RequestException as e:
            post_task_update(callback, f"*** Warning: Network error while creating ElevenLabs TTS mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        except IOError as e:
            post_task_update(callback, f"*** Warning: IOError while saving ElevenLabs TTS mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        except Exception as e:
            post_task_update(callback, f"*** Warning: unable to create ElevenLabs TTS mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        
## Use ipa-reader.xyz to create an mp3 for a piece of IPA text.
##
## Code slightly adapted from a solution found by Claudia

class IPAReaderEngine(TTSEngine):
    def __init__(self):
        self.tts_engine_type = 'ipa_reader'
        self.phonetic = True
        self.execute_url = "https://iawll6of90.execute-api.us-east-1.amazonaws.com/production"
        
        self.languages = { 'american': { 'language_id': 'american',
                                         'voices': [ 'Salli',
                                                     'Ivy',
                                                     'Joanna',
                                                     'Joey',
                                                     'Justin',
                                                     'Kendra',
                                                     'Kimberley'
                                                     ]
                                         },
                           'english': { 'language_id': 'american',
                                         'voices': [ 'Emma',
                                                     'Brian',
                                                     'Amy'
                                                     ]
                                         },
                           'australian': { 'language_id': 'australian',
                                           'voices': [ 'Nicole',
                                                       'Russell'
                                                       ]
                                           },
                           'french': { 'language_id': 'french',
                                       'voices': [ 'Celine',
                                                   'Mathieu'
                                                   ]
                                       },
                           'icelandic': { 'language_id': 'icelandic',
                                          'voices': [ 'Karl',
                                                      'Dora'
                                                      ]
                                          },
                           'romanian': { 'language_id': 'romanian',
                                         'voices': [ 'Carmen'
                                                      ]
                                         },
                           'dutch': { 'language_id': 'dutch',
                                      'voices': [ 'Lotte',
                                                  'Ruben'
                                                  ]
                                      },
                           'portuguese': { 'language_id': 'portuguese',
                                           'voices': [ 'Cristiano',
                                                       'Ines'
                                                       ]
                                      },
                           'german': { 'language_id': 'german',
                                       'voices': [ 'Marlene'
                                                   ]
                                      },
                           'italian': { 'language_id': 'italian',
                                        'voices': [ 'Carla',
                                                    'Giorgio'
                                                    ]
                                      },
                           'japanese': { 'language_id': 'japanese',
                                         'voices': [ 'Mizuki'
                                                     ]
                                      },
                           'norwegian': { 'language_id': 'norwegian',
                                          'voices': [ 'Liv'
                                                      ]
                                      },
                           'polish': { 'language_id': 'polish',
                                       'voices': [ 'Maja',
                                                   'Jan',
                                                   'Ewa'
                                                   ]
                                      },
                           'russian': { 'language_id': 'russian',
                                        'voices': [ 'Maxim',
                                                    'Tatyana'
                                                    ]
                                      },
                           'spanish': { 'language_id': 'spanish',
                                        'voices': [ 'Conchita'
                                                    ]
                                      },
                           'swedish': { 'language_id': 'swedish',
                                        'voices': [ 'Astrid'
                                                    ]
                                      },
                           'turkish': { 'language_id': 'turkish',
                                        'voices': [ 'Filiz'
                                                    ]
                                      },
                           'welsh': { 'language_id': 'welsh',
                                      'voices': [ 'Gwyneth'
                                                    ]
                                      },

                           }

    def create_mp3(self, language_id, voice_id, text, output_file, callback=None):
        try:
            payload = json.dumps({
              "text": f"/{text}/",  
              "voice": voice_id
            })
            
            headers = {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
              'Accept': '*/*',
              'Accept-Language': 'en-US,en;q=0.5',
              'Accept-Encoding': 'gzip, deflate, br',
              'Content-Type': 'application/json',
              'Origin': 'http://ipa-reader.xyz',
              'Connection': 'keep-alive',
              'Referer': 'http://ipa-reader.xyz/',
              'Sec-Fetch-Dest': 'empty',
              'Sec-Fetch-Mode': 'cors',
              'Sec-Fetch-Site': 'cross-site',
              'TE': 'trailers'
            }

            response = requests.request("POST", self.execute_url, headers=headers, data=payload)

            binary_data = response._content.decode('unicode_escape')

            # Decode the base64-encoded binary data
            decoded_data = base64.b64decode(binary_data)

            abs_output_file = absolute_local_file_name(output_file)

            with open(abs_output_file, "wb") as audio_file:
                audio_file.write(decoded_data)

            return True
                
        except requests.exceptions.RequestException as e:
            post_task_update(callback, f"*** Warning: Network error while creating ipa-reader mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        except IOError as e:
            post_task_update(callback, f"*** Warning: IOError while saving ipa-reader mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False
        except Exception as e:
            post_task_update(callback, f"*** Warning: unable to create ipa-reader mp3 for '{text}': '{str(e)}'\n{traceback.format_exc()}")
            return False


#TTS_ENGINES = [ABAIREngine(), GoogleTTSEngine(), OpenAITTSEngine(), ReadSpeakerEngine(), IPAReaderEngine()]
TTS_ENGINES = [ABAIREngine(), GoogleTTSEngine(), OpenAITTSEngine(), ElevenLabsEngine(), IPAReaderEngine()]

#TTS_ENGINES_OPENAI_FIRST = [ABAIREngine(), OpenAITTSEngine(), GoogleTTSEngine(), ReadSpeakerEngine(), IPAReaderEngine()]
TTS_ENGINES_OPENAI_FIRST = [ABAIREngine(), OpenAITTSEngine(), GoogleTTSEngine(), ElevenLabsEngine(), IPAReaderEngine()]

TTS_ENGINES_ELEVEN_LABS_FIRST = [ElevenLabsEngine(), ABAIREngine(), OpenAITTSEngine(), GoogleTTSEngine(), IPAReaderEngine()]

def create_tts_engine(engine_type):
    if engine_type == 'readspeaker':
        return ReadSpeakerEngine()
    elif engine_type == 'google':
        return GoogleTTSEngine()
    elif engine_type == 'abair':
        return ABAIREngine()
    elif engine_type == 'openai':
        return OpenAITTSEngine()
    elif engine_type == 'eleven_labs':
        return ElevenLabsEngine()
    elif engine_type == 'ipa_reader':
        return IPAReaderEngine()
    else:
        raise ValueError(f"Unknown TTS engine type: {engine_type}")
    
def get_tts_engine(language, words_or_segments='words', preferred_tts_engine=None, phonetic=False, callback=None):
    post_task_update(callback, f"--- clara_tts_api looking for TTS engine for '{language}', preferred = '{preferred_tts_engine}'")
    if words_or_segments == 'segments' and phonetic == False and preferred_tts_engine == 'openai':
        TTS_ENGINE_LIST_TO_USE = TTS_ENGINES_OPENAI_FIRST
    elif words_or_segments == 'segments' and phonetic == False and preferred_tts_engine == 'eleven_labs':
        TTS_ENGINE_LIST_TO_USE = TTS_ENGINES_ELEVEN_LABS_FIRST
    else:
        TTS_ENGINE_LIST_TO_USE = TTS_ENGINES 
    for tts_engine in TTS_ENGINE_LIST_TO_USE:
        if language in tts_engine.languages and tts_engine.phonetic == phonetic:
            post_task_update(callback, f"--- clara_tts_api found TTS engine of type '{tts_engine.tts_engine_type}'")
            return tts_engine
    return None

def tts_engine_type_supports_language(engine_type, language):
    if engine_type == 'openai':
        return True # OpenAI TTS is supposed to be multilingual, though quality varies a lot
    else:
        for tts_engine in TTS_ENGINES:
            if tts_engine.tts_engine_type == engine_type and language in tts_engine.languages:
                return True
        return False

def get_tts_engine_types():
    return [ tts_engine.tts_engine_type for tts_engine in TTS_ENGINES ]

def get_default_voice(language, preferred_voice, words_or_segments_or_phonemes, tts_engine=None):
    tts_engine = tts_engine or get_tts_engine(language)
    tts_engine_type = tts_engine.tts_engine_type
    if tts_engine and language in tts_engine.languages:
        voices = tts_engine.languages[language]['voices']
        # Choose the explicitly preferred voice if it's there
        if preferred_voice in voices:
            return preferred_voice
        # If we're using Google TTS, take the default voice for words - the high-end ones are usually only good
        # for longer inputs
        elif tts_engine_type == 'google' and words_or_segments_or_phonemes == 'words':
            return 'default'
        else:
            return voices[0]
    return None

def get_language_id(language, tts_engine=None):
    tts_engine = tts_engine or get_tts_engine(language)
    if tts_engine and language in tts_engine.languages:
        return tts_engine.languages[language]['language_id']
    return None
