# EP03 制作复盘：字幕、连续运动、配音与机械声

记录日期：2026-10-31。根据本轮用户反馈、实际产物及独立 QA 记录整理；本次仅更新文档，没有重新播放、听审、合成或渲染。

用户对连续运动版反馈“视频可以了”，随后要求机械声更明显、节奏稍快，并明确允许整片及旁白稍加快。该认可限定当前视觉基线，不等于认可后续增强版听感、通过全部 QA 或授权发布。

## 1. 字幕要记录成片中的实际位置

EP03 原字幕比用户认为正常的 EP02 低约151px。1080×1920 下，EP02 实际白字底边约 Y1530–1531、底距388–389px；原 EP03 底距只有237–238px。不能只比较 ASS 的 MarginV 或字号，不同 PlayRes、对齐方式和字体会改变实际位置。

本次保留 EP03 字体与字号，将 Subtitle 顶中锚点改为 `pos(540,1484)`，实际白字底边对齐 EP02；同时将“运动轨迹”Note 从 Y1500 移到 Y1410，避免上移字幕后撞字。后续沿用[字幕位置规范](subtitle-placement.md)，检查短句、最长句、近景及移动主体经过字幕带的情况。

这些是当前分辨率和样式的基准，不是任意画幅的通用坐标，也不代表实际平台 UI 遮挡测试通过。旁白字幕继续单行、每条最多20字符、同时仅一条。证据：[位置独审](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/subtitle-position-review-v1/independent/report.md)、[修复局部独审](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/subtitle-audio-fix-v2/qa/local-layout-report.md)。

## 2. 连续运动要检查机构位移及低速区间

旧120秒动作链累计42.5秒机构静止，最长一段12秒；部分时段只有相机在动。编码像素有变化、不存在相邻完全相同帧，不能证明机构持续运动。

有效修改是把原有因果动作铺满讲解区间，形成八段有限单程运动，不往返循环凑时长。初次仅删除 hold 仍沿用全段 smoothstep，低速区间最长约5.27秒；最终改为0.4秒余弦速度加减速窗，中段恒速，数值低于1mm/s最长约0.433秒。瞬时换向允许减速，不能靠极小的非零位移宣称观感流畅。

必须保留机械因果：讲“B 电机停止”时，B 驱动轮在72–99秒保持，A 路继续运动；不能为了“都在动”而让讲解失真。移动中的夹端近景需要跟随，箭头、标签、轨迹和拟音必须按新运动重算。完整新渲染只能复用同一冻结任务自己的预览帧，不能混用旧版本帧。

证据：[旧停段独立诊断](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/continuous-motion-v3/qa/old-motion-report.md)、[短加减速独审](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/continuous-motion-v3/qa/short-ramp-report.md)、[完整运动版 QA](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/continuous-motion-v3/qa/final/report.md)。数值、静态序列和解码仍不能替代实时观看。

## 3. 运动速度和拟音可闻性要分别控制

连续运动修复后，用户反馈“机械音不见了”。实际机械轨为−55.15 LUFS，旁白为−26.11 LUFS，分轨门控响度差约29.04 LU；机械声比前一版又下降6.71 LU，约96%功率集中80–250Hz。轨道存在并不能反驳用户听不到的感受，整体混音峰值合格也不能证明机械声可闻。

原因之一是拟音包络直接使用 `min(abs(du)/18,1)`：动作铺得更均匀、更慢，音量与载频也一起下降。以后改变运动曲线，必须重新核对机械分轨电平、频谱、旁白覆盖段和无旁白段；同步包络之外，还要单独安排合理的声音存在感。

本次制作+10dB、+16dB及+16dB加温和3/4/5次谐波的对照；选择后者作为待试听生产版本，不压低旁白、不对总混音硬限幅、不加每次换画面的冲击音。它增加中频线索，最终 AAC 真峰值−1.20dBTP，机械声仍明确为合成拟音。

**+16dB、谐波系数和−1dBTP上限均是本轮处理参数，不是以后每集直接套用的配方。** 手机可闻性、是否刺耳及是否遮盖旁白，要实际外放/耳机听审。证据：[分轨诊断](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/audio-qa/diagnosis.md)、[候选比较](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/audio-qa/candidates/report.md)。

## 4. 配音先理顺指代，再做必要的局部重录

保留当前打印机系列 `qwen3-tts-flash / Kai`。复杂关系句应跟随已经露出的结构：12秒先引导看橙带，16秒夹端近景再解释“两端连在同一个滑架”；轮子身份先说“它是 A 路转向轮”，再排除“不是 B 电机驱动轮”。不要为了字幕短句而每条重新起腔，也不要为了填静音而提前指向尚未出现的部件。

本次只替换 AD03/F04 两个完整旧单元，生成四句，保留其他七段；使用实测时长安排字幕和镜头。缺词级对齐时，不擅自按估算词界剪旧长段；句尾低幅能量只是候选，不能据此自动判吞字或反复重生成。证据：[最小配音交接](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/audio-optimization-v2/direction/handoff.md)。

## 5. 先明确“慢”的范围，再统一调速并核精确帧

“速度慢”可能指机器动作，也可能指整片节奏。此次明确询问后，用户选择整片及旁白稍快，才采用1.12倍：画面、音频、字幕及标签统一时刻映射，旁白使用 `atempo` 保音高，不重新合成、不升高 Kai 音调；时长约107.143秒，仍满足正式片至少90秒。

已认可的烧录字幕成片可统一调速，不能再次叠烧字幕。派生 SRT/ASS/timeline 的时刻也要除以倍率，ASS 内部淡入淡出时长同样缩放；原档保留。单纯检查总时长、帧数和流起止并不足够。

本次默认 `-r30` 的恒定帧率调度使画面固定落后约44–64ms，恰好暴露在字幕换句边界；无 seek 精确帧确认并非抽图误标。改用 `setpts=(PTS-STARTPTS)/1.12,fps=fps=30:start_time=0:round=near` 和 `-fps_mode passthrough`，新片五点误差约4–15.5ms，小于一帧。修画面时直接复制已核验 AAC，再独立验证载荷、时间戳及解码 PCM 一致，避免无必要的再次音频损失。

该组合是本次 FFmpeg 链路的有效修复，不保证所有链路都存在同一问题。调速后都应抽查首、中、尾和字幕切换边界；有疑点时无 seek 选精确帧，不能仅凭缩略图、文件名或名义 PTS 下结论。证据：[映射问题](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/qa/mapping/report.md)、[最终映射复核](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/qa/fpsfix-final/report.md)。

## 后续制作顺序

1. 锁定用户认可的片段、哈希和范围，保留原视频、原音频及归档。
2. 检查真实机构 hold、低速窗、字幕实际位置和分轨电平，再决定改哪一层。
3. 先做覆盖停段、近景、换向及旁白有/无区间的实际局部 A/B；有可测改善再全片。
4. 动作或时点变化后，同步检查投影、标签、字幕、轨迹与拟音；配音只改获授权且有依据的部分。
5. 对最终文件做完整解码、格式/时长/首尾/峰值检查，核对字幕换句和实际帧映射；复用未变资产时先核哈希。
6. 最后实际连续播放并用手机外放、耳机试听，分别记录生成状态、用户认可范围、技术结果和感知验收。

## 当前交付及未验证项

唯一最新记录见[交付清单](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/delivery-manifest.json)。当前影片 SHA256：`1fa11d7a5240611bd1f4adde237154a10bfab5f7dac41fb1e34eae3d0057351b`；3214帧，1080×1920/30fps，H.264/AAC，约107.143秒，全片解码通过。

用户尚未在本轮记录中认可该最新片的机械声和提速听感。手机可闻性、旁白自然度、AD03b句尾、完整实时音画语义及平台 UI 遮挡仍未全部验证，感知评分保持 null，状态 `NEEDS_REVIEW`。上述参数与技术检查不能写成爆款、平台增长或正式验收成功；详见[剩余试听项](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/human-review.md)。
