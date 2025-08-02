#!/usr/bin/env python3
"""
Gradio Demo: Text-to-Speech to Speech-to-Text Workflow

This demo application shows how to:
1. Convert text to speech using OpenAI's TTS API
2. Transcribe the generated audio back to SRT subtitles using Speechhall API

Requirements:
- Set OPENAI_API_KEY environment variable
- Set SPEECHALL_API_TOKEN environment variable
"""

import os
import tempfile
import time
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI
from speechall import ApiClient, Configuration
from speechall.api.speech_to_text_api import SpeechToTextApi
from speechall.models.transcription_model_identifier import TranscriptionModelIdentifier
from speechall.models.transcript_language_code import TranscriptLanguageCode
from speechall.models.transcript_output_format import TranscriptOutputFormat
from speechall.exceptions import ApiException

# Load environment variables
load_dotenv()


def setup_clients():
    """Set up both OpenAI and Speechall API clients."""
    # Check for required environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    speechall_token = os.getenv("SPEECHALL_API_TOKEN")
    
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    if not speechall_token:
        raise ValueError("SPEECHALL_API_TOKEN environment variable is required")
    
    # Setup OpenAI client
    openai_client = OpenAI(api_key=openai_key)
    
    # Setup Speechall client
    configuration = Configuration()
    configuration.access_token = speechall_token
    configuration.host = "https://api.speechall.com/v1"
    api_client = ApiClient(configuration)
    speechall_client = SpeechToTextApi(api_client)
    
    return openai_client, speechall_client


def text_to_speech(text, voice="alloy"):
    """Convert text to speech using OpenAI's TTS API."""
    if not text.strip():
        return None, "Please enter some text to convert to speech."
    
    try:
        openai_client, _ = setup_clients()
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name
        
        # Generate speech
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        # Save to temporary file
        response.stream_to_file(temp_path)
        
        return temp_path, f"✅ Audio generated successfully! ({len(text)} characters)"
        
    except Exception as e:
        return None, f"❌ Error generating speech: {str(e)}"


def speech_to_subtitle(audio_path, model_id="assemblyai.best", language="en"):
    """Convert speech to SRT subtitles using Speechall API."""
    if not audio_path:
        return "", "No audio file available. Please generate speech first."
    
    try:
        _, speechall_client = setup_clients()
        
        # Read audio file
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()
        
        # Make transcription request with SRT format
        result = speechall_client.transcribe(
            model=TranscriptionModelIdentifier(model_id),
            body=audio_data,
            language=TranscriptLanguageCode(language),
            output_format=TranscriptOutputFormat.SRT,
            punctuation=True,
        )
        
        # Get the SRT content
        srt_content = result.text
        
        return srt_content, f"✅ Subtitles generated successfully using {model_id}!"
        
    except ApiException as e:
        return "", f"❌ Speechall API Error: {str(e)}"
    except Exception as e:
        return "", f"❌ Error generating subtitles: {str(e)}"


def create_demo():
    """Create the Gradio demo interface."""
    with gr.Blocks(title="Text-to-Speech to Subtitle Demo") as demo:
        gr.Markdown("""
        # 🎤 Text-to-Speech to Subtitle Demo
        
        This demo shows how to use OpenAI's TTS API with Speechhall's speech-to-text API 
        to create subtitles for generated audio content.
        
        **Required Environment Variables:**
        - `OPENAI_API_KEY`: Your OpenAI API key
        - `SPEECHALL_API_TOKEN`: Your Speechhall API token
        """)
        
        # State to store audio file path
        audio_state = gr.State(None)
        
        with gr.Row():
            with gr.Column():
                text_input = gr.Textbox(
                    label="Text to Convert",
                    placeholder="Enter the text you want to convert to speech...",
                    lines=3
                )
                
                # Example text
                gr.Examples(
                    examples=[
                        ["Hello world! This is a test of the text-to-speech system. We will convert this text to audio, and then back to subtitles."],
                        ["Welcome to our amazing demo application. You can type any text here and it will be converted to speech using OpenAI's technology."],
                        ["The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet at least once."]
                    ],
                    inputs=[text_input]
                )
                
                voice_dropdown = gr.Dropdown(
                    choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                    value="alloy",
                    label="Voice Selection"
                )
                
                tts_button = gr.Button("🎵 Generate Speech", variant="primary")
                tts_status = gr.Textbox(label="TTS Status", interactive=False)
                
                audio_output = gr.Audio(
                    label="Generated Audio",
                    type="filepath"
                )
        
        with gr.Row():
            with gr.Column():
                model_dropdown = gr.Dropdown(
                    choices=["assemblyai.best", "openai.whisper-1", "deepgram.nova-2"],
                    value="assemblyai.best",
                    label="Transcription Model"
                )
                
                language_dropdown = gr.Dropdown(
                    choices=["en", "es", "fr", "de", "it", "pt", "nl"],
                    value="en",
                    label="Language"
                )
                
                stt_button = gr.Button("📝 Generate Subtitles", variant="secondary")
                stt_status = gr.Textbox(label="STT Status", interactive=False)
                
                subtitle_output = gr.Textbox(
                    label="Generated SRT Subtitles",
                    lines=10,
                    max_lines=20
                )
        
        # Event handlers
        def handle_tts(text, voice):
            audio_path, status = text_to_speech(text, voice)
            return audio_path, status, audio_path
        
        def handle_stt(audio_path, model, language):
            srt_content, status = speech_to_subtitle(audio_path, model, language)
            return srt_content, status
        
        tts_button.click(
            fn=handle_tts,
            inputs=[text_input, voice_dropdown],
            outputs=[audio_output, tts_status, audio_state]
        )
        
        stt_button.click(
            fn=handle_stt,
            inputs=[audio_state, model_dropdown, language_dropdown],
            outputs=[subtitle_output, stt_status]
        )

    
    return demo


if __name__ == "__main__":
    try:
        # Verify environment variables are set
        setup_clients()
        
        # Create and launch the demo
        demo = create_demo()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease set the required environment variables:")
        print("export OPENAI_API_KEY='your-openai-key'")
        print("export SPEECHALL_API_TOKEN='your-speechall-token'")
    except Exception as e:
        print(f"❌ Error starting demo: {e}")