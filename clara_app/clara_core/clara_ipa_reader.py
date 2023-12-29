"""
Use ipa-reader.xyz to create an mp3 for a piece of IPA text.

Code slightly adapted from a solution found by Claudia
"""

from .clara_utils import absolute_local_file_name

import requests
import json
import base64
import traceback

_execute_url = "https://iawll6of90.execute-api.us-east-1.amazonaws.com/production"

ipa_reader_voices = { 'american': [ { 'name': 'Salli', 'gender': 'female' },
                                    { 'name': 'Ivy', 'gender': 'female' },
                                    { 'name': 'Joanna', 'gender': 'female' },
                                    { 'name': 'Joey', 'gender': 'male' },
                                    { 'name': 'Justin', 'gender': 'male' },
                                    { 'name': 'Kendra', 'gender': 'female' },
                                    { 'name': 'Kimberley', 'gender': 'female' },
                                    ],
                      'english': [ { 'name': 'Emma', 'gender': 'female' },
                                   { 'name': 'Brian', 'gender': 'male' },
                                   { 'name': 'Amy', 'gender': 'female' },
                                   ],
                      'australian': [ { 'name': 'Nicole', 'gender': 'female' },
                                      { 'name': 'Russell', 'gender': 'male' },
                                      ],
                      'french': [ { 'name': 'Celine', 'gender': 'female' },
                                  { 'name': 'Mathieu', 'gender': 'male' },
                                  ],
                      'icelandic': [ { 'name': 'Dora', 'gender': 'female' },
                                     { 'name': 'Karl', 'gender': 'female' },
                                     ],
                      'romanian': [ { 'name': 'Carmen', 'gender': 'female' },
                                    ],
                      'dutch': [ { 'name': 'Lotte', 'gender': 'female' },
                                 { 'name': 'Ruben', 'gender': 'male' },
                                 ],
                      }
                      

def get_ipa_audio(ipa_text, voice_id, audio_file, callback=None):

    try:
        payload = json.dumps({
          #"text": "/ˈrɛnə(n)/",
          "text": f"/{ipa_text}/",  
          #"voice": "Ruben"
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

        response = requests.request("POST", _execute_url, headers=headers, data=payload)

        binary_data = response._content.decode('unicode_escape')

        # Decode the base64-encoded binary data
        decoded_data = base64.b64decode(binary_data)

        abs_audio_file = absolute_local_file_name(audio_file)

        with open(abs_audio_file, "wb") as audio_file:
            audio_file.write(decoded_data)
            
    except requests.exceptions.RequestException as e:
        post_task_update(callback, f"*** Warning: Network error while creating ipa-reader mp3 for '{ipa_text}': '{str(e)}'\n{traceback.format_exc()}")
        return False
    except IOError as e:
        post_task_update(callback, f"*** Warning: IOError while saving ipa-reader mp3 for '{ipa_text}': '{str(e)}'\n{traceback.format_exc()}")
        return False
    except Exception as e:
        post_task_update(callback, f"*** Warning: unable to create ipa-reader mp3 for '{ipa_text}': '{str(e)}'\n{traceback.format_exc()}")
        return False

                
