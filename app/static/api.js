/**
 * Briefly API 客户端
 * 提供与后端 API 交互的方法
 */

const API_BASE = '/api';

const api = {
    // ============ RSS 源管理 ============
    
    /**
     * 获取 RSS 源列表
     * @param {boolean} enabled - 可选，只获取启用的源
     * @returns {Promise<Array>} RSS 源列表
     */
    async getSources(enabled = null) {
        const params = new URLSearchParams();
        if (enabled !== null) {
            params.append('enabled', enabled);
        }
        const url = `${API_BASE}/sources${params.toString() ? '?' + params.toString() : ''}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('获取 RSS 源列表失败');
        return response.json();
    },
    
    /**
     * 获取单个 RSS 源
     * @param {number} id - RSS 源 ID
     * @returns {Promise<Object>} RSS 源详情
     */
    async getSource(id) {
        const response = await fetch(`${API_BASE}/sources/${id}`);
        if (!response.ok) throw new Error('获取 RSS 源失败');
        return response.json();
    },
    
    /**
     * 创建 RSS 源
     * @param {string} name - 名称
     * @param {string} url - RSS URL
     * @param {string} description - 描述（可选）
     * @returns {Promise<Object>} 创建的 RSS 源
     */
    async createSource(name, url, description = null) {
        const response = await fetch(`${API_BASE}/sources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, url, description })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '创建 RSS 源失败');
        }
        return response.json();
    },
    
    /**
     * 更新 RSS 源
     * @param {number} id - RSS 源 ID
     * @param {Object} data - 更新数据
     * @returns {Promise<Object>} 更新后的 RSS 源
     */
    async updateSource(id, data) {
        const response = await fetch(`${API_BASE}/sources/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('更新 RSS 源失败');
        return response.json();
    },
    
    /**
     * 删除 RSS 源
     * @param {number} id - RSS 源 ID
     */
    async deleteSource(id) {
        const response = await fetch(`${API_BASE}/sources/${id}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('删除 RSS 源失败');
    },
    
    /**
     * 切换 RSS 源启用状态
     * @param {number} id - RSS 源 ID
     * @returns {Promise<Object>} 更新后的 RSS 源
     */
    async toggleSource(id) {
        const response = await fetch(`${API_BASE}/sources/${id}/toggle`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('切换状态失败');
        return response.json();
    },
    
    /**
     * 测试 RSS 源连接
     * @param {string} url - RSS URL
     * @returns {Promise<Object>} 测试结果
     */
    async testSourceUrl(url) {
        const response = await fetch(`${API_BASE}/sources/${url}/test`);
        if (!response.ok) throw new Error('测试连接失败');
        return response.json();
    },
    
    // ============ 文章管理 ============
    
    /**
     * 获取文章列表
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>} 文章列表和分页信息
     */
    async getArticles(params = {}) {
        const queryParams = new URLSearchParams({
            page: params.page || 1,
            page_size: params.page_size || 20,
            ...params
        });
        const response = await fetch(`${API_BASE}/articles?${queryParams}`);
        if (!response.ok) throw new Error('获取文章列表失败');
        return response.json();
    },
    
    /**
     * 获取文章详情
     * @param {number} id - 文章 ID
     * @returns {Promise<Object>} 文章详情
     */
    async getArticle(id) {
        const response = await fetch(`${API_BASE}/articles/${id}`);
        if (!response.ok) throw new Error('获取文章失败');
        return response.json();
    },
    
    /**
     * 标记文章为已读
     * @param {number} id - 文章 ID
     * @returns {Promise<Object>} 更新后的文章
     */
    async markAsRead(id) {
        const response = await fetch(`${API_BASE}/articles/${id}/read`, {
            method: 'PUT'
        });
        if (!response.ok) throw new Error('标记已读失败');
        return response.json();
    },
    
    /**
     * 切换收藏状态
     * @param {number} id - 文章 ID
     * @returns {Promise<Object>} 更新后的文章
     */
    async toggleFavorite(id) {
        const response = await fetch(`${API_BASE}/articles/${id}/favorite`, {
            method: 'PUT'
        });
        if (!response.ok) throw new Error('切换收藏失败');
        return response.json();
    },
    
    /**
     * 获取收藏文章列表
     * @param {number} page - 页码
     * @param {number} pageSize - 每页数量
     * @returns {Promise<Object>} 文章列表和分页信息
     */
    async getFavorites(page = 1, pageSize = 20) {
        const response = await fetch(`${API_BASE}/articles/favorites?page=${page}&page_size=${pageSize}`);
        if (!response.ok) throw new Error('获取收藏列表失败');
        const articles = await response.json();
        return {
            articles: articles,
            total: articles.length,
            page: page,
            page_size: pageSize
        };
    },
    
    /**
     * 获取过滤文章列表
     * @param {number} page - 页码
     * @param {number} pageSize - 每页数量
     * @returns {Promise<Object>} 文章列表和分页信息
     */
    async getFilteredArticles(page = 1, pageSize = 20) {
        const response = await fetch(`${API_BASE}/articles/filtered?page=${page}&page_size=${pageSize}`);
        if (!response.ok) throw new Error('获取过滤列表失败');
        const articles = await response.json();
        return {
            articles: articles,
            total: articles.length,
            page: page,
            page_size: pageSize
        };
    },
    
    /**
     * 获取关键词匹配的文章列表
     * @param {number} page - 页码
     * @param {number} pageSize - 每页数量
     * @returns {Promise<Object>} 文章列表和分页信息
     */
    async getKeywordMatchedArticles(page = 1, pageSize = 20) {
        const response = await fetch(`${API_BASE}/articles/keywords?page=${page}&page_size=${pageSize}`);
        if (!response.ok) throw new Error('获取关键词匹配列表失败');
        const articles = await response.json();
        return {
            articles: articles,
            total: articles.length,
            page: page,
            page_size: pageSize
        };
    },
    
    /**
     * 获取文章统计信息
     * @returns {Promise<Object>} 统计信息
     */
    async getStatistics() {
        const response = await fetch(`${API_BASE}/articles/statistics`);
        if (!response.ok) throw new Error('获取统计信息失败');
        return response.json();
    },
    
    /**
     * 为文章生成摘要
     * @param {number} id - 文章 ID
     * @returns {Promise<Object>} 生成结果
     */
    async generateSummary(id) {
        const response = await fetch(`${API_BASE}/articles/${id}/summarize`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '生成摘要失败');
        }
        return response.json();
    },
    
    /**
     * 推送文章到 Webhook
     * @param {number} id - 文章 ID
     * @returns {Promise<Object>} 推送结果
     */
    async sendToWebhook(id) {
        const response = await fetch(`${API_BASE}/articles/${id}/webhook`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '推送失败');
        }
        return response.json();
    },
    
    // ============ 关键词管理 ============
    
    /**
     * 获取关键词列表
     * @param {boolean} enabled - 可选，只获取启用的关键词
     * @returns {Promise<Array>} 关键词列表
     */
    async getKeywords(enabled = null) {
        const params = new URLSearchParams();
        if (enabled !== null) {
            params.append('enabled', enabled);
        }
        const url = `${API_BASE}/keywords${params.toString() ? '?' + params.toString() : ''}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('获取关键词列表失败');
        return response.json();
    },
    
    /**
     * 创建关键词
     * @param {string} keyword - 关键词
     * @returns {Promise<Object>} 创建的关键词
     */
    async createKeyword(keyword) {
        const response = await fetch(`${API_BASE}/keywords`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '创建关键词失败');
        }
        return response.json();
    },
    
    /**
     * 更新关键词
     * @param {number} id - 关键词 ID
     * @param {Object} data - 更新数据
     * @returns {Promise<Object>} 更新后的关键词
     */
    async updateKeyword(id, data) {
        const response = await fetch(`${API_BASE}/keywords/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('更新关键词失败');
        return response.json();
    },
    
    /**
     * 删除关键词
     * @param {number} id - 关键词 ID
     */
    async deleteKeyword(id) {
        const response = await fetch(`${API_BASE}/keywords/${id}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('删除关键词失败');
    },
    
    /**
     * 切换关键词启用状态
     * @param {number} id - 关键词 ID
     * @returns {Promise<Object>} 更新后的关键词
     */
    async toggleKeyword(id) {
        const response = await fetch(`${API_BASE}/keywords/${id}/toggle`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('切换状态失败');
        return response.json();
    },
    
    /**
     * 批量删除关键词
     * @param {Array<number>} ids - 关键词 ID 列表
     * @returns {Promise<Object>} 删除结果
     */
    async bulkDeleteKeywords(ids) {
        const response = await fetch(`${API_BASE}/keywords/bulk-delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ids)
        });
        if (!response.ok) throw new Error('批量删除失败');
        return response.json();
    },
    
    /**
     * 测试关键词匹配
     * @param {string} keyword - 关键词
     * @param {string} text - 测试文本
     * @returns {Promise<Object>} 测试结果
     */
    async testKeywordMatch(keyword, text) {
        const params = new URLSearchParams({ keyword, text });
        const response = await fetch(`${API_BASE}/keywords/test?${params}`);
        if (!response.ok) throw new Error('测试失败');
        return response.json();
    },
    
    /**
     * 应用关键词过滤
     * @returns {Promise<Object>} 过滤结果
     */
    async applyKeywordFilter() {
        const response = await fetch(`${API_BASE}/keywords/apply-filter`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('应用过滤失败');
        return response.json();
    },
    
    // ============ 系统管理 ============
    
    /**
     * 健康检查
     * @returns {Promise<Object>} 健康状态
     */
    async healthCheck() {
        const response = await fetch(`${API_BASE}/health`);
        if (!response.ok) throw new Error('健康检查失败');
        return response.json();
    },
    
    /**
     * 获取系统状态
     * @returns {Promise<Object>} 系统状态
     */
    async getStatus() {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) throw new Error('获取状态失败');
        return response.json();
    },
    
    /**
     * 立即触发 RSS 抓取（后台执行，立即返回）
     * @returns {Promise<Object>} 启动状态
     */
    async triggerFetchNow() {
        const response = await fetch(`${API_BASE}/fetch/start`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('触发抓取失败');
        return response.json();
    },
    
    /**
     * 手动触发 RSS 抓取（同步执行，等待完成）
     * @returns {Promise<Object>} 抓取结果
     */
    async triggerFetch() {
        const response = await fetch(`${API_BASE}/fetch`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('触发抓取失败');
        return response.json();
    },
    
    /**
     * 手动触发 AI 总结
     * @returns {Promise<Object>} 总结结果
     */
    async triggerSummarize() {
        const response = await fetch(`${API_BASE}/summarize`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('触发总结失败');
        return response.json();
    },
    
    /**
     * 运行完整流程
     * @returns {Promise<Object>} 流程结果
     */
    async runPipeline() {
        const response = await fetch(`${API_BASE}/run-pipeline`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('运行流程失败');
        return response.json();
    },
    
    /**
     * 测试 AI 功能
     * @returns {Promise<Object>} 测试结果
     */
    async testAI() {
        const response = await fetch(`${API_BASE}/test/ai`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('测试 AI 失败');
        return response.json();
    },
    
    /**
     * 测试 RSS 抓取
     * @param {string} url - RSS URL
     * @returns {Promise<Object>} 测试结果
     */
    async testRss(url) {
        const response = await fetch(`${API_BASE}/test/rss?url=${encodeURIComponent(url)}`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('测试 RSS 失败');
        return response.json();
    },
    
    /**
     * 测试 Webhook 连接
     * @returns {Promise<Object>} 测试结果
     */
    async testWebhook() {
        const response = await fetch(`${API_BASE}/test/webhook`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('测试 Webhook 失败');
        return response.json();
    },
    
    /**
     * 启动定时任务调度器
     * @returns {Promise<Object>} 启动结果
     */
    async startScheduler() {
        const response = await fetch(`${API_BASE}/scheduler/start`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('启动调度器失败');
        return response.json();
    },
    
    /**
     * 停止定时任务调度器
     * @returns {Promise<Object>} 停止结果
     */
    async stopScheduler() {
        const response = await fetch(`${API_BASE}/scheduler/stop`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('停止调度器失败');
        return response.json();
    },
    
    // ============ AI 设置管理 ============
    
    /**
     * 获取 AI 配置
     * @returns {Promise<Object>} AI 配置信息
     */
    async getAIConfig() {
        const response = await fetch(`${API_BASE}/ai/config`);
        if (!response.ok) throw new Error('获取 AI 配置失败');
        return response.json();
    },
    
    /**
     * 保存 AI 设置
     * @param {Object} settings - AI 设置
     * @param {string} settings.api_key - API Key
     * @param {string} settings.base_url - Base URL
     * @param {string} settings.model - 模型名称
     * @param {number} settings.max_summary_length - 最大摘要长度
     * @param {boolean} settings.enabled - 是否启用
     * @returns {Promise<Object>} 保存结果
     */
    async saveAISettings(settings) {
        const response = await fetch(`${API_BASE}/ai/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        if (!response.ok) throw new Error('保存 AI 设置失败');
        return response.json();
    },
    
    /**
     * 验证 API Key
     * @returns {Promise<Object>} 验证结果
     */
    async validateAIKey() {
        const response = await fetch(`${API_BASE}/ai/validate`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('验证 API Key 失败');
        return response.json();
    }
};
