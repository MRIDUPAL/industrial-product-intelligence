import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const hiddenEvidenceFields = [
  "brand",
  "model",
  "name",
  "category",
  "description",
];

function normalizeCategory(category) {
  if (!category) return "Uncategorized";

  const value = category.trim().toLowerCase();

  if (value.includes("plug") && value.includes("socket")) {
    return "Plugs & Sockets";
  }

  if (value.includes("power tool")) return "Power Tool";
  if (value.includes("protective coating")) return "Protective Coating";
  if (value.includes("capacitor") && value.includes("contactor")) {
    return "Capacitor Duty Contactors";
  }
  if (value.includes("solenoid") && value.includes("brake")) {
    return "Solenoid Brakes";
  }

  return category.trim();
}

function App() {
  const [products, setProducts] = useState([]);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  async function loadProducts() {
    const response = await fetch(`${API_URL}/products`);

    if (!response.ok) {
      throw new Error("Could not load products");
    }

    const productData = await response.json();

    const realProducts = productData.filter(
      (product) =>
        product.brand?.toLowerCase() !== "string" &&
        product.model?.toLowerCase() !== "string" &&
        product.name?.toLowerCase() !== "string"
    );

    const uniqueProducts = [
      ...new Map(
        realProducts.map((product) => [
          `${product.brand}|${product.model}|${product.name}`,
          product,
        ])
      ).values(),
    ];

    const productsWithEvidence = await Promise.all(
      uniqueProducts.map(async (product) => {
        const evidenceResponse = await fetch(
          `${API_URL}/products/${product.id}/evidence`
        );

        return {
          ...product,
          evidence: evidenceResponse.ok
            ? await evidenceResponse.json()
            : [],
        };
      })
    );

    setProducts(productsWithEvidence);
    setLoading(false);
  }

  useEffect(() => {
    loadProducts().catch(() => {
      setStatus("Could not load products.");
      setLoading(false);
    });
  }, []);

  async function handleImport(event) {
    event.preventDefault();

    if (!file) {
      setStatus("Choose a PDF first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setStatus("Extracting PDF with Gemini...");

    try {
      const response = await fetch(`${API_URL}/ai/import-pdf`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("PDF import failed");
      }

      const result = await response.json();

      setStatus(
        `Imported ${result.name} with ${result.evidence_count} evidence records.`
      );

      setFile(null);
      await loadProducts();
    } catch (error) {
      setStatus(error.message);
    }
  }

  const categories = [
    ...new Set(
      products
        .map((product) => normalizeCategory(product.category))
        .filter(Boolean)
    ),
  ].sort();

  const normalizedSearch = searchTerm.trim().toLowerCase();

  const filteredProducts = products.filter((product) => {
    const searchableText = [
      product.name,
      product.brand,
      product.model,
      product.description,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const matchesSearch = searchableText.includes(normalizedSearch);

    const matchesCategory =
      categoryFilter === "all" ||
      normalizeCategory(product.category) === categoryFilter;

    return matchesSearch && matchesCategory;
  });

  return (
    <main className="dashboard">
      <header>
        <p className="eyebrow">Industrial Product Intelligence</p>
        <h1>Product catalog</h1>
        <p className="subtitle">
          Extract, enrich, and trace industrial product information.
        </p>
      </header>

      <section className="product-card import-card">
        <h2>Import product PDF</h2>

        <form onSubmit={handleImport}>
          <input
            type="file"
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button type="submit">Import PDF</button>
        </form>

        {status && <p>{status}</p>}
      </section>

      <section className="filters">
        <input
          type="search"
          placeholder="Search products, brands, or models..."
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
        />

        <select
          value={categoryFilter}
          onChange={(event) => setCategoryFilter(event.target.value)}
        >
          <option value="all">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </section>

      <p className="result-count">
        Showing {filteredProducts.length} of {products.length} products
      </p>

      {loading ? (
        <p>Loading products...</p>
      ) : filteredProducts.length === 0 ? (
        <p className="empty-state">No matching products found.</p>
      ) : (
        <section className="product-grid">
          {filteredProducts.map((product) => {
            const technicalEvidence = (product.evidence || []).filter(
              (item) =>
                !hiddenEvidenceFields.includes(
                  item.field_name?.toLowerCase()
                )
            );

            const specifications = Array.isArray(product.specifications)
              ? product.specifications
              : Object.entries(product.specifications || {}).map(
                  ([key, value]) => ({ key, value })
                );

            return (
              <article className="product-card" key={product.id}>
                <span className="category">
                  {normalizeCategory(product.category)}
                </span>

                <h2>{product.name || "Unnamed product"}</h2>

                <p className="brand">
                  {product.brand || "Unknown brand"} ·{" "}
                  {product.model || "Unknown model"}
                </p>

                <p>
                  {product.description || "No description available."}
                </p>

                <details>
                  <summary>
                    Specifications ({specifications.length})
                  </summary>

                  {specifications.length > 0 ? (
                    <ul>
                      {specifications.map((item, index) => (
                        <li key={`${item.key}-${index}`}>
                          <strong>{item.key}:</strong> {String(item.value)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No specifications recorded.</p>
                  )}
                </details>

                <details>
                  <summary>
                    Evidence ({technicalEvidence.length})
                  </summary>

                  {technicalEvidence.length > 0 ? (
                    <ul>
                      {technicalEvidence.map((item) => (
                        <li key={item.id}>
                          <strong>{item.field_name}:</strong> {item.value}
                          {item.source_url && (
                            <>
                              <br />
                              <a
                                href={item.source_url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                View source
                              </a>
                            </>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No additional evidence recorded.</p>
                  )}
                </details>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}

export default App;