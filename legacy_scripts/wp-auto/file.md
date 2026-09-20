这是一个语言学习类Web应用（类似Teco Lab的英语学习平台）。

---

## 📋 产品需求文档（PRD）

### 1. 产品概述

**产品名称：** 沉浸式语言学习平台  
**产品定位：** 专为提升英语**口语**和**听力**设计的视频学习工具  
**核心用户：** 英语学习者（中级到高级），希望用过真实语料提升语言能力

### 2. 核心功能模块

#### 2.1 视频播放器模块
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 视频播放控制 | 播放/暂停、进度条拖拽 | P0 |
| 倍速播放 | 0.5x / 0.75x / 1x / 1.25x / 1.5x | P0 |
| 循环模式 | 视频循环播放 | P1 |
| 单句循环 | 当前句子重复播放 | P1 |
| 单句暂停 | 每句播放完自动暂停 | P1 |

#### 2.2 字幕系统（核心功能）
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 多语言字幕 | 双语 / 纯英 / 中文 / 音标(IPA) | P0 |
| 动态高亮 | 当前播放句子高亮显示 | P0 |
| 点击跳转 | 点击字幕跳转到对应时间点 | P0 |
| 逐句展示 | 当前句子独立显示（大屏模式） | P1 |
| 关键词标色 | 重点词汇彩色标注 | P1 |
| 整句音标 | 句子级别IPA音标显示 | P2 |

#### 2.3 词典/释义系统
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 点击查词 | 点击任意单词弹出释义卡片 | P0 |
| 音标显示 | 单词音标（IPA） | P0 |
| 中文释义 | 简明中文翻译 | P0 |
| 英文释义 | 英英解释 | P1 |
| 例句展示 | 包含该词的例句 | P1 |
| 收藏单词 | 加入生词本 | P2 |

#### 2.4 学习模式
| 模式 | 描述 | 优先级 |
|------|------|--------|
| 正常模式 | 标准播放+字幕 | P0 |
| 听写模式 | 隐藏部分文本，用户填空 | P0 |
| 跟读模式 | 录音对比，评分反馈 | P1 |
| 影子跟读 | 延迟0.5-1秒跟读训练 | P2 |
| 回音法 | 单句重复跟读训练 | P2 |

#### 2.5 内容管理
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 课程列表 | 按"期数"组织内容（第X期） | P0 |
| 分类标签 | 购物/美食/健身/旅行等20+类别 | P1 |
| 难度评级 | 1-5星难度标识 | P2 |
| 进度记录 | 学习进度保存 | P2 |

### 3. 页面布局与交互

#### 3.1 主要页面结构

```
【视频学习页】布局（桌面端 - 三栏式）
┌─────────────────────────────────────────────────────────────┐
│  ← 返回    标题: 第X期 / 视频标题          [跟读练习] [信息]   │
├──────────────────────┬──────────────────────┬───────────────┤
│                      │                      │               │
│   🎥 视频播放器       │   📝 动态字幕区域     │   🎯 练习/     │
│   (占左/上区域)       │   - 双语对照          │    信息面板    │
│                      │   - 逐句高亮          │               │
│   控制栏:            │   - 点击查词          │   跟读录音      │
│   [音标][倍速][←][⏸][→][循环][继续]        │   词卡详情      │
│                      │                      │               │
├──────────────────────┴──────────────────────┴───────────────┤
│  [视频倍速] [多种字幕] [打印字幕] [音频下载] [整句音标]...    │
│  （功能标签栏）                                               │
└─────────────────────────────────────────────────────────────┘

【移动端】布局
- 视频在上，占满宽度
- 字幕区域在下，可滚动
- 底部固定控制栏
```

#### 3.2 交互细节

**字幕交互：**
- 当前播放句子高亮（黄色背景 #FFF3CD 或柔和高亮）
- 关键词彩色标注（红色=重点词，蓝色=短语，绿色=其他）
- 点击单词 → 弹出词典卡片（悬浮窗）
- 词典卡片位置：优先右侧，空间不足时下侧

**播放器交互：**
- 上一句/下一句按钮快速跳转
- 空格键 = 播放/暂停
- 左右箭头 = 快进/快退3秒

---

## 🛠️ 技术文档

### 1. 技术栈建议

| 层级 | 推荐方案 | 备选方案 |
|------|---------|---------|
| 前端框架 | React 18 + TypeScript | Vue 3 |
| 状态管理 | Zustand / Jotai | Redux Toolkit |
| UI组件库 | Tailwind CSS + 自定义组件 | Ant Design |
| 视频播放 | Video.js / Plyr | HTML5 Video API |
| 音频处理 | Web Audio API | RecordRTC |
| 后端服务 | Node.js + Express / NestJS | Python FastAPI |
| 数据库 | PostgreSQL + Redis | MongoDB |
| 文件存储 | AWS S3 / 阿里云OSS | 本地存储 |
| 部署 | Docker + Kubernetes | Vercel / Netlify |

### 2. 数据模型设计

```typescript
// 视频内容模型
interface Video {
  id: string;
  episodeNumber: number;      // 第X期
  title: string;              // 标题
  description?: string;
  videoUrl: string;           // 视频文件URL
  thumbnailUrl: string;       // 封面图
  duration: number;           // 总时长（秒）
  difficulty: 1 | 2 | 3 | 4 | 5;  // 难度星级
  categories: string[];       // 标签：["购物", "美食", "健身"]
  subtitles: Subtitle[];      // 字幕列表
  createdAt: Date;
  updatedAt: Date;
}

// 字幕条目模型
interface Subtitle {
  id: string;
  videoId: string;
  index: number;              // 句子序号
  startTime: number;          // 开始时间（秒）
  endTime: number;            // 结束时间（秒）
  textEN: string;             // 英文原文
  textZH?: string;            // 中文翻译
  ipa?: string;               // 整句音标
  words: WordToken[];         // 分词信息（用于高亮）
  isKeySentence?: boolean;    // 是否重点句
}

// 分词/词汇模型
interface WordToken {
  text: string;               // 单词文本
  startIndex: number;         // 在句子中的起始位置
  endIndex: number;
  type: 'normal' | 'keyword' | 'phrase' | 'idom';  // 词类型
  wordId?: string;            // 关联词典ID
}

// 词典词条模型
interface DictionaryEntry {
  id: string;
  word: string;               // 单词
  phoneticUK?: string;        // 英式音标
  phoneticUS?: string;        // 美式音标
  translations: Translation[];
  examples: Example[];
  audioUrl?: string;          // 发音音频
}

interface Translation {
  pos: string;                // 词性：n./v./adj.
  meaning: string;            // 中文释义
  meaningEN?: string;         // 英文释义
}

interface Example {
  sentence: string;
  translation: string;
}

// 用户学习记录
interface UserProgress {
  userId: string;
  videoId: string;
  currentTime: number;        // 上次观看位置
  completed: boolean;
  dictationResults: DictationResult[];
  recordingResults: RecordingResult[];
}

// 听写记录
interface DictationResult {
  subtitleId: string;
  userInput: string;
  isCorrect: boolean;
  attemptCount: number;
}

// 录音/跟读记录
interface RecordingResult {
  subtitleId: string;
  audioUrl: string;
  score?: number;             // AI评分（0-100）
  feedback?: string;          // 改进建议
}
```

### 3. 核心组件架构

```
src/
├── components/
│   ├── VideoPlayer/           # 视频播放器
│   │   ├── VideoPlayer.tsx    # 主播放器组件
│   │   ├── ControlBar.tsx     # 播放控制栏
│   │   ├── SpeedSelector.tsx  # 倍速选择器
│   │   └── hooks/
│   │       ├── useVideoState.ts
│   │       └── useKeyboardShortcuts.ts
│   │
│   ├── Subtitle/              # 字幕系统
│   │   ├── SubtitlePanel.tsx  # 字幕面板容器
│   │   ├── BilingualSubtitle.tsx  # 双语字幕行
│   │   ├── WordHighlighter.tsx    # 单词高亮组件
│   │   ├── DictionaryPopup.tsx    # 词典弹窗
│   │   └── IPAOverlay.tsx         # 音标覆盖层
│   │
│   ├── Practice/              # 练习模式
│   │   ├── DictationMode.tsx  # 听写模式
│   │   ├── ShadowingMode.tsx  # 影子跟读
│   │   ├── RecordingPanel.tsx # 录音面板
│   │   └── AudioWaveform.tsx  # 波形可视化
│   │
│   └── common/                # 通用组件
│       ├── StarRating.tsx
│       ├── CategoryTags.tsx
│       └── EpisodeCard.tsx
│
├── hooks/
│   ├── useCurrentSubtitle.ts  # 获取当前时间对应的字幕
│   ├── useRecording.ts        # 录音控制
│   ├── useDictionary.ts       # 词典查询
│   └── useProgressSync.ts     # 学习进度同步
│
├── services/
│   ├── api.ts                 # API客户端
│   ├── subtitleParser.ts      # 字幕解析（SRT/VTT/JSON）
│   ├── audioProcessor.ts      # 音频处理（Web Audio）
│   └── scoringEngine.ts       # 语音评分（集成第三方API）
│
├── stores/
│   ├── videoStore.ts          # 视频播放状态
│   ├── subtitleStore.ts       # 字幕状态
│   └── userStore.ts           # 用户状态
│
├── types/
│   └── index.ts               # TypeScript类型定义
│
└── utils/
    ├── timeFormatter.ts       # 时间格式化
    ├── textSegmenter.ts       # 文本分词
    └── localStorage.ts        # 本地存储封装
```

### 4. 关键算法与逻辑

#### 4.1 字幕时间同步算法

```typescript
// hooks/useCurrentSubtitle.ts
export const useCurrentSubtitle = (
  subtitles: Subtitle[],
  currentTime: number
) => {
  return useMemo(() => {
    // 二分查找当前时间对应的字幕
    const index = binarySearch(subtitles, currentTime, (s, t) => {
      if (t < s.startTime) return -1;
      if (t > s.endTime) return 1;
      return 0;
    });
    return subtitles[index] || null;
  }, [subtitles, currentTime]);
};

// 自动滚动到当前字幕
useEffect(() => {
  if (currentSubtitleRef.current) {
    currentSubtitleRef.current.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }
}, [currentSubtitle]);
```

#### 4.2 单词分词与标注

```typescript
// utils/textSegmenter.ts
interface Token {
  text: string;
  type: 'word' | 'punctuation' | 'space';
  isKeyWord?: boolean;
  wordData?: DictionaryEntry;
}

export const segmentSubtitle = (
  text: string,
  keyWords: string[]
): Token[] => {
  // 使用Intl.Segmenter进行语言感知分词
  const segmenter = new Intl.Segmenter('en', { granularity: 'word' });
  const segments = Array.from(segmenter.segment(text));
  
  return segments.map(seg => {
    const isKeyWord = keyWords.includes(seg.segment.toLowerCase());
    return {
      text: seg.segment,
      type: seg.isWordLike ? 'word' : 'punctuation',
      isKeyWord,
      // 后续可关联词典数据
    };
  });
};
```

#### 4.3 录音与评分流程

```typescript
// hooks/useRecording.ts
export const useRecording = () => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    
    mediaRecorder.ondataavailable = (event) => {
      audioChunksRef.current.push(event.data);
    };
    
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      await processRecording(audioBlob);
    };
    
    mediaRecorder.start();
    setIsRecording(true);
  };

  // 集成语音评分API（如Azure Speech/科大讯飞）
  const processRecording = async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('reference_text', currentSubtitleText);
    
    const response = await fetch('/api/speech/score', {
      method: 'POST',
      body: formData
    });
    return response.json(); // { score, feedback, phoneme_scores }
  };

  return { isRecording, startRecording, stopRecording };
};
```

### 5. API 接口设计

```yaml
# RESTful API 设计

# 视频内容
GET   /api/videos                    # 获取视频列表（支持分类、难度筛选）
GET   /api/videos/:id                # 获取视频详情（含字幕）
GET   /api/videos/:id/subtitles      # 获取字幕（支持格式：json/srt/vtt）
GET   /api/videos/:id/audio          # 获取音频文件（用于下载）

# 词典
GET   /api/dictionary/search?q=word  # 搜索单词
GET   /api/dictionary/:wordId        # 获取词条详情
POST  /api/dictionary/favorites      # 收藏单词

# 学习进度
GET   /api/progress/:videoId         # 获取某视频学习进度
POST  /api/progress                  # 更新学习进度
GET   /api/progress/stats            # 学习统计

# 语音评分
POST  /api/speech/score              # 提交录音获取评分
POST  /api/speech/feedback           # 获取发音反馈

# 听写练习
POST  /api/dictation/check           # 提交听写答案
GET   /api/dictation/history         # 获取听写历史
```

### 6. 性能优化要点

| 优化项 | 方案 |
|--------|------|
| 视频加载 | 分段加载（HLS/DASH），首屏预加载前30秒 |
| 字幕渲染 | 虚拟滚动（字幕多时），避免DOM过多 |
| 词典查询 | 本地词典缓存 + IndexedDB，减少网络请求 |
| 录音处理 | Web Worker中处理音频编码，不阻塞主线程 |
| 状态管理 | 细粒度订阅，避免不必要的重渲染 |

### 7. 第三方服务集成

| 服务 | 用途 | 推荐方案 |
|------|------|---------|
| 视频存储/CDN | 视频文件分发 | 阿里云OSS + CDN / AWS S3 + CloudFront |
| 语音转文字 | 视频自动生成字幕 | 阿里云智能语音 / Azure Speech |
| 语音评分 | 口语评测 | 科大讯飞语音评测 / Azure Pronunciation Assessment |
| 实时通信 | 多人学习房间（可选） | Socket.io / WebRTC |

### 8. 开发里程碑

| 阶段 | 周期 | 交付内容 |
|------|------|---------|
| MVP | 4周 | 视频播放 + 双语字幕 + 点击查词 |
| V1.0 | +3周 | 听写模式 + 录音功能 + 用户系统 |
| V1.5 | +2周 | 跟读评分 + 学习进度 + 移动端适配 |
| V2.0 | +4周 | AI推荐 + 社区功能 + 数据分析 |

---

这份文档涵盖了从产品设计到技术实现的完整蓝图。如需进一步细化某个模块（如具体的React组件代码、数据库Schema、或部署配置），请告诉我！