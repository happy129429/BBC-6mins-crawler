# BBC-6mins-crawler
Languages: [English](README.md) / [简体中文](README-zh.md)

A simple set of Python scripts for batch-crawling the audio and transcripts of BBC Learning English's 6 Minute English programs from the official BBC website.

Specifically, it currently contains two relatively independent scripts: the JSON generator and the downloader. The JSON generator collects the metadata of all available programs (title, link, etc.) from the homepage at once and saves it in a JSON document. The downloader then reads the JSON data and downloads the transcript and audio file for each program sequentially, while adding key-value pairs such as `media_download_url` to the JSON file.

The main part of the scripts in this simple crawler project was generated with the assistance of AI (DeepSeek LLM, specifically). The human author came up with the idea and is responsible for code review and debugging, with AI assistance.

The source code of this project is licensed under the GNU General Public License v3.0. BBC content, including audio and transcripts, is not a part of this project and thus not covered by this license.

This project is not affiliated with or endorsed by the BBC. All BBC content remains the property of its respective rights holders. If you are a rights holder and have any concerns about this project or its distribution of content, please contact me and I will promptly remove or modify the relevant material.

(For more details, please refer to the Chinese version of this README.)
