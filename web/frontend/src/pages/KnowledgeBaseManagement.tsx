import React, { useState, useEffect, useCallback } from 'react';
import { Search, Plus, Edit2, Trash2, BookOpen, Tag, Eye, Filter, Download } from 'lucide-react';
import { exportToCSV } from '../hooks/useKeyboardShortcuts';
import { fetchWithTimeout } from '../api/fallback';

interface Category {
  id: number;
  name: string;
  description?: string | null;
}

interface Tag {
  id: number;
  name: string;
  color?: string;
}

interface Article {
  id: number;
  title: string;
  content: string;
  category_id?: number | null;
  tag_ids: number[];
  author?: string | null;
  is_published: boolean;
  views: number;
  created_at?: string;
  updated_at?: string;
}

interface ArticleFormData {
  title: string;
  content: string;
  category_id: number | null;
  tag_ids: number[];
  author: string;
  is_published: boolean;
}

const ITEMS_PER_PAGE = 10;

const KnowledgeBaseManagement: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [formData, setFormData] = useState<ArticleFormData>({
    title: '',
    content: '',
    category_id: null,
    tag_ids: [],
    author: '',
    is_published: false,
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [articleToDelete, setArticleToDelete] = useState<Article | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithTimeout('/api/knowledge-base/articles', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items: Article[] = Array.isArray(data) ? data : data.items || [];
      setArticles(items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch articles');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetchWithTimeout('/api/knowledge-base/categories', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCategories(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error('Failed to fetch categories:', err);
    }
  }, []);

  const fetchTags = useCallback(async () => {
    try {
      const res = await fetchWithTimeout('/api/knowledge-base/tags', { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTags(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error('Failed to fetch tags:', err);
    }
  }, []);

  useEffect(() => {
    fetchArticles();
    fetchCategories();
    fetchTags();
  }, [fetchArticles, fetchCategories, fetchTags]);

  const filtered = articles.filter((a) => {
    const matchesSearch =
      !search ||
      a.title.toLowerCase().includes(search.toLowerCase()) ||
      a.content.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !categoryFilter || a.category_id === Number(categoryFilter);
    return matchesSearch && matchesCategory;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const paginated = filtered.slice((safePage - 1) * ITEMS_PER_PAGE, safePage * ITEMS_PER_PAGE);

  const getCategoryName = (id: number | null | undefined) => {
    if (!id) return 'Uncategorized';
    return categories.find((c) => c.id === id)?.name || 'Unknown';
  };

  const getTagNames = (ids: number[]) => {
    return ids.map((id) => tags.find((t) => t.id === id)?.name || `#${id}`);
  };

  const openCreate = () => {
    setEditingArticle(null);
    setFormData({ title: '', content: '', category_id: null, tag_ids: [], author: '', is_published: false });
    setShowForm(true);
  };

  const openEdit = (article: Article) => {
    setEditingArticle(article);
    setFormData({
      title: article.title,
      content: article.content,
      category_id: article.category_id ?? null,
      tag_ids: article.tag_ids,
      author: article.author || '',
      is_published: article.is_published,
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const url = editingArticle
        ? `/api/knowledge-base/articles/${editingArticle.id}`
        : '/api/knowledge-base/articles';
      const method = editingArticle ? 'PUT' : 'POST';
      const res = await fetchWithTimeout(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      await fetchArticles();
    } catch (err: any) {
      setError(err.message || 'Failed to save article');
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = (article: Article) => {
    setArticleToDelete(article);
    setShowDeleteConfirm(true);
  };

  const handleDelete = async () => {
    if (!articleToDelete) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetchWithTimeout(`/api/knowledge-base/articles/${articleToDelete.id}`, { method: 'DELETE', headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(false);
      setArticleToDelete(null);
      await fetchArticles();
    } catch (err: any) {
      setError(err.message || 'Failed to delete article');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleTag = (tagId: number) => {
    setFormData((prev) => ({
      ...prev,
      tag_ids: prev.tag_ids.includes(tagId)
        ? prev.tag_ids.filter((id) => id !== tagId)
        : [...prev.tag_ids, tagId],
    }));
  };

  const inputCls =
    'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-500';
  const btnPrimary =
    'px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none';
  const btnSecondary =
    'px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded font-medium transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none';
  const btnDanger =
    'px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none';

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <BookOpen size={28} className="text-cyan-400" />
            <h1 className="text-2xl font-bold">Knowledge Base</h1>
          </div>
          <button onClick={openCreate} className={btnPrimary} aria-label="Create new article">
            <Plus size={16} className="inline mr-1" /> New Article
          </button>
          <button onClick={() => exportToCSV(filtered as unknown as Record<string, unknown>[], "knowledge_base_export.csv")} className="px-4 py-2 bg-green-700 hover:bg-green-600 text-white rounded font-medium transition-colors inline-flex items-center gap-1" aria-label="Export articles as CSV">
            <Download size={16} /> Export CSV
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200" role="alert" aria-live="assertive">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-4 mb-4">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search articles..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
              className={`${inputCls} pl-9 max-w-xs`}
              aria-label="Search articles"
            />
          </div>
          <div className="relative">
            <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <select
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value); setCurrentPage(1); }}
              className={`${inputCls} pl-9 max-w-xs`}
              aria-label="Filter by category"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400" role="status" aria-live="polite">Loading articles...</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-700">
              <table className="w-full text-sm" role="table">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Title</th>
                    <th className="px-4 py-3 text-left font-semibold">Category</th>
                    <th className="px-4 py-3 text-left font-semibold">Tags</th>
                    <th className="px-4 py-3 text-left font-semibold">Author</th>
                    <th className="px-4 py-3 text-center font-semibold">Views</th>
                    <th className="px-4 py-3 text-center font-semibold">Status</th>
                    <th className="px-4 py-3 text-center font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-16 text-center">
                        <div className="text-5xl mb-4">📚</div>
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">No articles yet</h3>
                        <p className="text-gray-400 mb-4">Get started by adding your first knowledge base article.</p>
                        <button onClick={openCreate} className="bg-cyan-600 hover:bg-cyan-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none" aria-label="Create new article">
                          <Plus size={16} className="inline mr-1" /> New Article
                        </button>
                      </td>
                    </tr>
                  ) : (
                    paginated.map((article) => (
                      <tr key={article.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-100">{article.title}</div>
                          <div className="text-xs text-gray-400 truncate max-w-xs">{article.content.substring(0, 80)}...</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 bg-gray-700 rounded text-xs">{getCategoryName(article.category_id)}</span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {getTagNames(article.tag_ids).map((name) => (
                              <span key={name} className="px-2 py-0.5 bg-cyan-900/40 text-cyan-300 rounded text-xs">
                                <Tag size={10} className="inline mr-0.5" />{name}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-300">{article.author || '—'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-flex items-center gap-1 text-gray-300">
                            <Eye size={12} /> {article.views}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${article.is_published ? 'bg-green-900/50 text-green-300' : 'bg-yellow-900/50 text-yellow-300'}`}>
                            {article.is_published ? 'Published' : 'Draft'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center space-x-2">
                          <button
                            onClick={() => openEdit(article)}
                            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none"
                            aria-label={`Edit article ${article.title}`}
                          >
                            <Edit2 size={12} className="inline" /> Edit
                          </button>
                          <button
                            onClick={() => confirmDelete(article)}
                            className="px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-xs transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:outline-none"
                            aria-label={`Delete article ${article.title}`}
                          >
                            <Trash2 size={12} className="inline" /> Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-400">
                Showing {paginated.length} of {filtered.length} articles
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                  className={btnSecondary + ' disabled:opacity-50'}
                  aria-label="Go to previous page"
                >
                  Previous
                </button>
                <span className="px-3 py-2 text-sm">Page {safePage} of {totalPages}</span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                  className={btnSecondary + ' disabled:opacity-50'}
                  aria-label="Go to next page"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label={editingArticle ? 'Edit article' : 'Create article'}>
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg border border-gray-700 max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">{editingArticle ? 'Edit Article' : 'Create Article'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm mb-1">Title</label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    className={inputCls}
                    aria-label="Article title"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">Content</label>
                  <textarea
                    required
                    rows={6}
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    className={inputCls}
                    aria-label="Article content"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">Category</label>
                  <select
                    value={formData.category_id || ''}
                    onChange={(e) => setFormData({ ...formData, category_id: e.target.value ? Number(e.target.value) : null })}
                    className={inputCls}
                    aria-label="Article category"
                  >
                    <option value="">Uncategorized</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm mb-1">Tags</label>
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => toggleTag(tag.id)}
                        className={`px-3 py-1 rounded text-xs transition-colors ${formData.tag_ids.includes(tag.id) ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
                        aria-label={`Toggle tag ${tag.name}`}
                        aria-pressed={formData.tag_ids.includes(tag.id)}
                      >
                        <Tag size={10} className="inline mr-0.5" />{tag.name}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm mb-1">Author</label>
                  <input
                    type="text"
                    value={formData.author}
                    onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                    className={inputCls}
                    aria-label="Article author"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_published"
                    checked={formData.is_published}
                    onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                    className="rounded bg-gray-700 border-gray-600 text-cyan-500 focus:ring-cyan-500"
                    aria-label="Published"
                  />
                  <label htmlFor="is_published" className="text-sm">Published</label>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setShowForm(false)} className={btnSecondary} aria-label="Cancel article form">
                    Cancel
                  </button>
                  <button type="submit" disabled={submitting} className={btnPrimary} aria-label={editingArticle ? 'Update article' : 'Create article'}>
                    {submitting ? 'Saving...' : editingArticle ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showDeleteConfirm && articleToDelete && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Confirm delete article">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm border border-gray-700">
              <h2 className="text-xl font-bold mb-2">Confirm Delete</h2>
              <p className="text-gray-300 mb-6">
                Are you sure you want to delete <strong>{articleToDelete.title}</strong>? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => { setShowDeleteConfirm(false); setArticleToDelete(null); }}
                  className={btnSecondary}
                  aria-label="Cancel delete"
                >
                  Cancel
                </button>
                <button onClick={handleDelete} disabled={submitting} className={btnDanger} aria-label={`Confirm delete article ${articleToDelete.title}`}>
                  {submitting ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeBaseManagement;
