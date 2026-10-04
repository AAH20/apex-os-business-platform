import React, { useState, useRef, useEffect } from 'react';
import { Package, Search, Download } from 'lucide-react';
import { productApi, type Product } from '../api/client';

const ProductManagement: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState({ name: '', sku: '', price: 0, category: '' });
  const [searchQuery, setSearchQuery] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const modalRef = useRef<HTMLDivElement>(null);
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isModalOpen && firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, [isModalOpen]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredProducts(products);
    } else {
      setFilteredProducts(productApi.search(searchQuery, ['name', 'sku', 'category']));
    }
  }, [products, searchQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingProduct) {
      productApi.update(editingProduct.id, formData);
      setAnnouncement(`Product "${formData.name}" updated successfully`);
    } else {
      productApi.create(formData);
      setAnnouncement(`Product "${formData.name}" added successfully`);
    }
    setProducts(productApi.getAll());
    closeModal();
  };

  const handleEdit = (product: Product) => {
    setEditingProduct(product);
    setFormData({ name: product.name, sku: product.sku, price: product.price, category: product.category });
    setIsModalOpen(true);
  };

  const handleDelete = (product: Product) => {
    productApi.delete(product.id);
    setProducts(productApi.getAll());
    setAnnouncement(`Product "${product.name}" removed`);
  };

  const handleExport = () => {
    const csv = productApi.export(
      ['id', 'name', 'sku', 'price', 'category'],
      ['ID', 'Name', 'SKU', 'Price', 'Category']
    );
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'products.csv';
    a.click();
    URL.revokeObjectURL(url);
    setAnnouncement('Products exported to CSV');
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingProduct(null);
    setFormData({ name: '', sku: '', price: 0, category: '' });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isModalOpen) {
      closeModal();
    }
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold mb-4 text-gray-100">Product Management</h1>

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setIsModalOpen(true)}
          aria-label="Add new product"
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
        >
          + Add Product
        </button>
        <button
          onClick={handleExport}
          aria-label="Export products to CSV"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 flex items-center gap-2"
        >
          <Download size={16} /> Export CSV
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <Search size={16} className="text-gray-400" />
          <input
            type="text"
            placeholder="Search products..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search products"
            className="border border-gray-600 rounded px-3 py-2 bg-gray-800 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </div>
      </div>

      {filteredProducts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-gray-800 rounded-lg">
          <Package className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-gray-100 text-lg mb-4">{searchQuery ? 'No products match your search.' : 'No products found. Create your first product!'}</p>
          <button
            onClick={() => setIsModalOpen(true)}
            aria-label="Create product"
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
          >
            Create Product
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table role="table" aria-label="Products list" className="min-w-full border-collapse border border-gray-700">
            <thead>
              <tr>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Name</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">SKU</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Price</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Category</th>
                <th scope="col" className="border border-gray-700 px-4 py-2 bg-gray-800 text-gray-100">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map(product => (
                <tr key={product.id}>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{product.name}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{product.sku}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">${product.price.toFixed(2)}</td>
                  <td className="border border-gray-700 px-4 py-2 text-gray-100">{product.category}</td>
                  <td className="border border-gray-700 px-4 py-2">
                    <button
                      onClick={() => handleEdit(product)}
                      aria-label={`Edit product ${product.name}`}
                      className="bg-yellow-500 text-white px-3 py-1 rounded mr-2 hover:bg-yellow-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:ring-offset-2"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(product)}
                      aria-label={`Delete product ${product.name}`}
                      className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="product-modal-title"
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div ref={modalRef} className="bg-gray-800 p-6 rounded-lg shadow-lg w-full max-w-md">
            <h2 id="product-modal-title" className="text-xl font-bold mb-4 text-gray-100">
              {editingProduct ? 'Edit Product' : 'Add New Product'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="product-name" className="block text-sm font-medium mb-1 text-gray-100">Name</label>
                <input
                  ref={firstInputRef}
                  id="product-name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  aria-label="Product name"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="product-sku" className="block text-sm font-medium mb-1 text-gray-100">SKU</label>
                <input
                  id="product-sku"
                  type="text"
                  value={formData.sku}
                  onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                  aria-label="Product SKU"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="product-price" className="block text-sm font-medium mb-1 text-gray-100">Price</label>
                <input
                  id="product-price"
                  type="number"
                  step="0.01"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
                  aria-label="Product price"
                  aria-required="true"
                  required
                  min="0"
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="mb-4">
                <label htmlFor="product-category" className="block text-sm font-medium mb-1 text-gray-100">Category</label>
                <input
                  id="product-category"
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  aria-label="Product category"
                  aria-required="true"
                  required
                  className="w-full border border-gray-600 rounded px-3 py-2 bg-gray-900 text-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  aria-label="Cancel"
                  className="bg-gray-600 text-gray-100 px-4 py-2 rounded hover:bg-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 focus-visible:ring-offset-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  aria-label={editingProduct ? 'Save product changes' : 'Add product'}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-2"
                >
                  {editingProduct ? 'Save' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductManagement;
