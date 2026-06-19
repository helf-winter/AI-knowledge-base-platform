const LABELS: Record<string, string> = {
  active: '启用中',
  ai_expand: 'AI 知识扩充',
  answer_quality: '回答质量审核',
  answer_without_sources: '回答缺少依据',
  approve: '建议通过',
  approved: '已通过',
  archive_metadata: '归档知识条目',
  auto_extract: '自动提取',
  auto_learning: '自动学习',
  auto_learning_draft: '自动学习草稿',
  available: '可用',
  batch_import: '批量导入',
  chat_stream: 'AI 问答',
  chat_stream_failed: 'AI 问答失败',
  clustered: '已聚类',
  completed: '已完成',
  completed_with_errors: '完成但有异常',
  confidential: '机密',
  conversation: '问答会话',
  create: '创建新知识库',
  create_gap: '创建知识缺口',
  create_metadata: '创建知识条目',
  delete_document: '删除文档',
  delete_metadata: '删除知识条目',
  department: '部门知识',
  disabled: '已停用',
  document: '知识文档',
  document_access: '文档访问审核',
  document_summarize: '文档总结',
  drafted: '已生成草稿',
  empty: '无任务',
  failed: '失败',
  fallback_to_general_answer: '已切换通用回答',
  feedback: '用户反馈',
  high: '高风险',
  incomplete_answer: '回答不完整',
  internal: '内部',
  knowledge_compare: '知识对比',
  knowledge_extract: '知识抽取',
  knowledge_gap: '知识缺口',
  knowledge_metadata: '知识条目',
  knowledge_publish: '知识发布审核',
  knowledge_search: '知识检索',
  login: '登录',
  low: '低风险',
  low_confidence_answer: '低置信度问答',
  manual_import: '手动导入',
  medium: '中风险',
  merged: '已合并',
  needs_review: '需重新审核',
  negative_user_feedback: '用户反馈不佳',
  none: '未提交',
  open: '待处理',
  parse_document: '解析文档',
  pending: '待处理',
  personal: '个人知识',
  policy: '制度规范',
  private: '私有',
  processing: '解析中',
  public: '公有知识',
  reject: '建议拒绝',
  rejected: '已拒绝',
  restricted: '受限',
  review: '建议人工复核',
  review_metadata: '审核知识条目',
  reviewing: '审核中',
  ignored: '暂不处理',
  running: '执行中',
  secret: '绝密',
  succeeded: '成功',
  task: '后台任务',
  update_metadata: '更新知识条目',
  upload: '上传导入',
  upload_document: '上传文档',
  queued: '排队中',
  extracting_text: '提取文本中',
  chunking: '切分知识片段中',
  embedding: '生成语义向量中',
  stalled: '可能已中断',
};

export function displayLabel(value?: string | null, fallback = '-') {
  if (!value) return fallback;
  return LABELS[value] ?? value;
}

export const actionLabel = displayLabel;
export const issueTypeLabel = displayLabel;
export const knowledgeSpaceLabel = displayLabel;
export const knowledgeTypeLabel = displayLabel;
export const metadataStatusLabel = displayLabel;
export const parseStatusLabel = displayLabel;
export const publishStatusLabel = displayLabel;
export const resourceTypeLabel = displayLabel;
export const reviewStatusLabel = displayLabel;
export const riskLevelLabel = displayLabel;
export const sourceTypeLabel = displayLabel;
export const suggestionLabel = displayLabel;
export const taskStatusLabel = displayLabel;
export const taskTypeLabel = displayLabel;
export const visibilityLabel = displayLabel;
