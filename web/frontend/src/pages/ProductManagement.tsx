import React, { useState, useEffect, useCallback } from 'react';

interface Product {
  id: number;
  name: string;
  price: number;
  stock: number;
  category: string;
}

interface ProductFormData {
  name: string;
  price: number;
  stock: number;
  category: string;
}

const ITEMS_PER_PAGE = 10;

const ProductManagement: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState<ProductFormData>({
    name: '',
    price: 0,
    stock: 0,
    category: '',
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [productToDelete, setProductToDelete] = useState<Product | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/products/');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items: Product[] = Array.isArray(data) ? data : data.items || [];
      setProducts(items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch products');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const categories = Array.from(new Set(products.map((p) => p.category).filter(Boolean)));

  const filtered = products.filter((p) => {
    const matchesSearch =
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.category.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !categoryFilter || p.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const paginated = filtered.slice((safePage - 1) * ITEMS_PER_PAGE, safePage * ITEMS_PER_PAGE);

  const openCreate = () => {
    setEditingProduct(null);
    setFormData({ name: '', price: 0, stock: 0, category: '' });
    setShowForm(true);
  };

  const openEdit = (product: Product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      price: product.price,
      stock: product.stock,
      category: product.category,
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const url = editingProduct
        ? `/api/products/${editingProduct.id}/`
        : '/api/products/';
      const method = editingProduct ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      await fetchProducts();
    } catch (err: any) {
      setError(err.message || 'Failed to save product');
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = (product: Product) => {
    setProductToDelete(product);
    setShowDeleteConfirm(true);
  };

  const handleDelete = async () => {
    if (!productToDelete) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/products/${productToDelete.id}/`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowDeleteConfirm(false);
      setProductToDelete(null);
      await fetchProducts();
    } catch (err: any) {
      setError(err.message || 'Failed to delete product');
    } finally {
      setSubmitting(false);
    }
  };

  const inputCls =
    'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500';
  const btnPrimary =
    'px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none';
  const btnSecondary =
    'px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none';
  const btnDanger =
    'px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none';

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Product Management</h1>
          <button onClick={openCreate} className={btnPrimary} aria-label="Create new product">
            + New Product
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200" role="alert" aria-live="assertive">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-4 mb-4">
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            className={`${inputCls} max-w-xs`}
            aria-label="Search products"
          />
          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setCurrentPage(1);
            }}
            className={`${inputCls} max-w-xs`}
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400" role="status" aria-live="polite">Loading products...</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-700">
              <table className="w-full text-sm" role="table">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">ID</th>
                    <th className="px-4 py-3 text-left font-semibold">Name</th>
                    <th className="px-4 py-3 text-left font-semibold">Category</th>
                    <th className="px-4 py-3 text-right font-semibold">Price</th>
                    <th className="px-4 py-3 text-right font-semibold">Stock</th>
                    <th className="px-4 py-3 text-center font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-16 text-center">
                        <div className="text-5xl mb-4">🏷️</div>
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">No products yet</h3>
                        <p className="text-gray-400 mb-4">Get started by adding your first product.</p>
                        <button onClick={openCreate} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none" aria-label="Create new product">
                          + New Product
                        </button>
                      </td>
                    </tr>
                  ) : (
                    paginated.map((product) => (
                      <tr key={product.id} className="border-t border-gray-700 hover:bg-gray-800/50">
                        <td className="px-4 py-3">{product.id}</td>
                        <td className="px-4 py-3">{product.name}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-1 bg-gray-700 rounded text-xs">
                            {product.category}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">${product.price.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right">{product.stock}</td>
                        <td className="px-4 py-3 text-center space-x-2">
                          <button
                            onClick={() => openEdit(product)}
                            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                            aria-label={`Edit product ${product.name}`}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => confirmDelete(product)}
                            className="px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-xs transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                            aria-label={`Delete product ${product.name}`}
                          >
                            Delete
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
                Showing {paginated.length} of {filtered.length} products
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
                <span className="px-3 py-2 text-sm">
                  Page {safePage} of {totalPages}
                </span>
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
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label={editingProduct ? 'Edit product' : 'Create product'}>
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700">
              <h2 className="text-xl font-bold mb-4">
                {editingProduct ? 'Edit Product' : 'Create Product'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className={inputCls}
                    aria-label="Product name"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">Category</label>
                  <input
                    type="text"
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className={inputCls}
                    aria-label="Product category"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm mb-1">Price</label>
                    <input
                      type="number"
                      required
                      min="0"
                      step="0.01"
                      value={formData.price}
                      onChange={(e) =>
                        setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })
                      }
                      className={inputCls}
                      aria-label="Product price"
                    />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Stock</label>
                    <input
                      type="number"
                      required
                      min="0"
                      value={formData.stock}
                      onChange={(e) =>
                        setFormData({ ...formData, stock: parseInt(e.target.value) || 0 })
                      }
                      className={inputCls}
                      aria-label="Product stock"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className={btnSecondary}
                    aria-label="Cancel product form"
                  >
                    Cancel
                  </button>
                  <button type="submit" disabled={submitting} className={btnPrimary} aria-label={editingProduct ? 'Update product' : 'Create product'}>
                    {submitting ? 'Saving...' : editingProduct ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showDeleteConfirm && productToDelete && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Confirm delete product">
            <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm border border-gray-700">
              <h2 className="text-xl font-bold mb-2">Confirm Delete</h2>
              <p className="text-gray-300 mb-6">
                Are you sure you want to delete <strong>{productToDelete.name}</strong>? This action
                cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setProductToDelete(null);
                  }}
                  className={btnSecondary}
                  aria-label="Cancel delete"
                >
                  Cancel
                </button>
                <button onClick={handleDelete} disabled={submitting} className={btnDanger} aria-label={`Confirm delete product ${productToDelete.name}`}>
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

export default ProductManagement;
