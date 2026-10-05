import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSort } from "../hooks/useSort";
import { useKeyboardShortcuts, exportToCSV } from "../hooks/useKeyboardShortcuts";

interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  stock: number;
}

interface ProductFormData {
  name: string;
  description: string;
  price: number;
  category: string;
  stock: number;
}

const EMPTY_FORM: ProductFormData = {
  name: "",
  description: "",
  price: 0,
  category: "",
  stock: 0,
};

const API_BASE = "/api/products";
const PAGE_SIZE = 10;

const ProductCRUD: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [formData, setFormData] = useState<ProductFormData>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const { sortedData: sortedFilteredProducts, requestSort, getSortIndicator } = useSort(filteredProducts);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}?page=${currentPage}&limit=${PAGE_SIZE}`, { headers: { 'X-API-Key': 'test-api-key-12345' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProducts(data.items || []);
      setTotalPages(Math.ceil((data.total || 0) / PAGE_SIZE));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch products");
    } finally {
      setLoading(false);
    }
  }, [currentPage]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  useEffect(() => {
    let result = products;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(term) ||
          p.description.toLowerCase().includes(term)
      );
    }
    if (categoryFilter) {
      result = result.filter((p) => p.category === categoryFilter);
    }
    setFilteredProducts(result);
  }, [products, searchTerm, categoryFilter]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "price" || name === "stock" ? Number(value) : value,
    }));
  };

  const openCreateForm = () => {
    setFormData(EMPTY_FORM);
    setEditingId(null);
    setIsFormOpen(true);
  };

  const openEditForm = (product: Product) => {
    setFormData({
      name: product.name,
      description: product.description,
      price: product.price,
      category: product.category,
      stock: product.stock,
    });
    setEditingId(product.id);
    setIsFormOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const url = editingId ? `${API_BASE}/${editingId}` : API_BASE;
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", "X-API-Key": "test-api-key-12345" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setIsFormOpen(false);
      setFormData(EMPTY_FORM);
      setEditingId(null);
      fetchProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save product");
    }
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE", headers: { "X-API-Key": "test-api-key-12345" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDeleteConfirmId(null);
      fetchProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete product");
    }
  };

  const categories = Array.from(new Set(products.map((p) => p.category).filter(Boolean)));

  // Keyboard shortcuts
  const searchRef = useRef<HTMLInputElement>(null);
  useKeyboardShortcuts({ onNew: openCreateForm, onSearch: () => searchRef.current?.focus(), searchRef, onExport: () => exportToCSV(products as unknown as Record<string, unknown>[], "product_export.csv"), onDelete: () => { if (products.length > 0) setDeleteConfirmId(products[0].id); }, onClose: () => setIsFormOpen(false) });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Product Management</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-800 text-red-200 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-4 mb-6">
        <input
          type="text"
          placeholder="Search products..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border rounded px-3 py-2 flex-1 min-w-[200px]"
         ref={searchRef}/>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="border rounded px-3 py-2"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
        <button
          onClick={openCreateForm}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        > title="Ctrl+N"
          + New Product
        </button>
      </div>

      {isFormOpen && (
        <form onSubmit={handleSubmit} className="bg-gray-800 shadow rounded p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">
            {editingId ? "Edit Product" : "Create Product"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <input
                name="category"
                value={formData.category}
                onChange={handleInputChange}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Price</label>
              <input
                name="price"
                type="number"
                step="0.01"
                value={formData.price}
                onChange={handleInputChange}
                required
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Stock</label>
              <input
                name="stock"
                type="number"
                value={formData.stock}
                onChange={handleInputChange}
                required
                className="w-full border rounded px-3 py-2"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows={3}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              {editingId ? "Update" : "Create"}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsFormOpen(false);
                setEditingId(null);
                setFormData(EMPTY_FORM);
              }}
              className="bg-gray-700 px-4 py-2 rounded hover:bg-gray-600"
            > title="Escape to close" Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-center py-8">Loading...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse bg-gray-800 shadow rounded">
            <thead>
              <tr className="bg-gray-900">
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('id')}>ID{getSortIndicator('id')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('name')}>Name{getSortIndicator('name')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('category')}>Category{getSortIndicator('category')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('price')}>Price{getSortIndicator('price')}</th>
                <th className="border px-4 py-2 text-left cursor-pointer select-none" onClick={() => requestSort('stock')}>Stock{getSortIndicator('stock')}</th>
                <th className="border px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedFilteredProducts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="border px-4 py-4 text-center text-gray-400">
                    No products found
                  </td>
                </tr>
              ) : (
                sortedFilteredProducts.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-900">
                    <td className="border px-4 py-2">{product.id}</td>
                    <td className="border px-4 py-2">{product.name}</td>
                    <td className="border px-4 py-2">{product.category}</td>
                    <td className="border px-4 py-2">${product.price.toFixed(2)}</td>
                    <td className="border px-4 py-2">{product.stock}</td>
                    <td className="border px-4 py-2">
                      <button
                        onClick={() => openEditForm(product)}
                        className="bg-yellow-500 text-white px-3 py-1 rounded text-sm mr-2 hover:bg-yellow-600"
                      >
                        Edit
                      </button>
                      {deleteConfirmId === product.id ? (
                        <>
                          <button
                            onClick={() => handleDelete(product.id)}
                            className="bg-red-600 text-white px-3 py-1 rounded text-sm mr-2"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="bg-gray-700 px-3 py-1 rounded text-sm"
                          > title="Escape to close" Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(product.id)}
                          className="bg-red-900/500 text-white px-3 py-1 rounded text-sm hover:bg-red-600"
                        > title="Delete key to delete" Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Prev
          </button>
          <span className="px-3 py-1">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default ProductCRUD;
