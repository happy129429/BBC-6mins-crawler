# 第三方依赖许可声明（THIRD PARTY LICENSES）

本项目（GPL-3.0）依赖以下第三方组件。均通过 pip 按用户环境安装、不随本仓库分发副本；
本文件用于集中声明其许可证与版权信息，满足各许可证的保留声明要求。

版本为 2026-08-28 本地验证值，以各项目官方仓库为准。

## 一、运行依赖

| 组件 | 版本（验证时） | 许可证 | 版权/作者 |
|---|---|---|---|
| requests | 2.31.0 | Apache-2.0 | Kenneth Reitz 等，PSF 成员项目 |
| beautifulsoup4 | 4.15.0 | MIT | Leonard Richardson |
| soupsieve | 2.9.2 | MIT | Isaac Muse |
| urllib3 | 2.0.7 | MIT | Andrey Petrov 等 |
| certifi | 2023.11.17 | MPL-2.0 | Kenneth Reitz |
| idna | 3.6 | BSD-3-Clause | Kim Davies |
| charset-normalizer / chardet | — | MIT / LGPL-2.1+ | Ahmed TAHRI / Daniel Blanc 等 |

## 二、开发与测试依赖

| 组件 | 版本（验证时） | 许可证 |
|---|---|---|
| pytest | 9.1.1 | MIT |
| iniconfig | 2.3.0 | MIT |
| pluggy | 1.6.0 | MIT |
| packaging | 26.3 | Apache-2.0 或 BSD-2-Clause（双许可） |

## 三、可选外部工具（独立程序，非 Python 包）

| 工具 | 许可证 | 说明 |
|---|---|---|
| yt-dlp | Unlicense（公有领域贡献） | 处理 mpd 流媒体清单时由用户自行安装 |
| ffmpeg | LGPL-2.1+（常见构建含 GPL 组件） | 视频转音频时由用户自行安装 |

外部工具作为独立程序使用，不随本项目分发；其许可义务由用户自身的安装与使用方式决定。

## 四、与本项目许可证（GPL-3.0）的兼容性

- Apache-2.0、MIT、BSD、Unlicense 均与 GPLv3 兼容；
- MPL-2.0 与 GPLv3 兼容（文件级 copyleft，不影响本项目整体授权）；
- chardet 的 LGPL-2.1+ 仅在 pip 解析出该备选依赖时涉及，作为库链接使用满足 LGPL 条款；
- 结论：**无许可证冲突，本项目可依 GPL-3.0 合规分发**。

## 五、许可证文本

### MIT License（beautifulsoup4、soupsieve、urllib3、pytest、iniconfig、pluggy、charset-normalizer）

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### BSD 3-Clause License（idna）

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

### BSD 2-Clause License（packaging 备选许可）

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

### Apache License 2.0（requests、packaging 备选许可）

全文见 <https://www.apache.org/licenses/LICENSE-2.0>。
依据其条款保留版权与声明：本产品包含 Apache License 2.0 授权的软件；
如附有 NOTICE 文件的内容，须同样保留。

### Mozilla Public License 2.0（certifi）

全文见 <https://www.mozilla.org/en-US/MPL/2.0/>。
文件级 copyleft：仅影响 MPL 覆盖的源文件本身，不影响本项目整体授权。

### Unlicense（yt-dlp）

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or distribute
this software, either in source code form or as a compiled binary, for any
purpose, commercial or non-commercial, and by any means.

### LGPL-2.1+（chardet、ffmpeg）

全文见 <https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>。
以库形式链接使用即满足条款；如随衍生作品分发，须随附 LGPL 文本并允许用户替换该库。
