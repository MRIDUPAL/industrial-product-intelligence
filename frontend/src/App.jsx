import { useEffect, useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

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
  const [datasetFile, setDatasetFile] = useState(null);
  const [status, setStatus] = useState("");
  const [datasetStatus, setDatasetStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [datasetProcessing, setDatasetProcessing] = useState(false);

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

  async function handleDatasetProcess(event) {
    event.preventDefault();

    if (!datasetFile) {
      setDatasetStatus("Choose an input CSV first.");
      return;
    }

    setDatasetProcessing(true);
    setDatasetStatus("Enriching product dataset...");

    const formData = new FormData();
    formData.append("file", datasetFile);

    try {
      const response = await fetch(`${API_URL}/datasets/process`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);

        throw new Error(
          errorBody?.detail || "Dataset processing failed."
        );
      }

      const outputBlob = await response.blob();
      const downloadUrl = URL.createObjectURL(outputBlob);
      const link = document.createElement("a");

      link.href = downloadUrl;
      link.download = "industrial_product_output.csv";
      link.click();

      URL.revokeObjectURL(downloadUrl);

      setDatasetStatus(
        "Dataset enriched and downloaded successfully."
      );
    } catch (error) {
      setDatasetStatus(error.message);
    } finally {
      setDatasetProcessing(false);
    }
  }

  const categories = [
    ...new Set(
      products.map((product) => normalizeCategory(product.category))
    ),
  ].sort();

  const search = searchTerm.trim().toLowerCase();

  const filteredProducts = products.filter((product) => {
    const text = [
      product.name,
      product.brand,
      product.model,
      product.description,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return (
      text.includes(search) &&
      (categoryFilter === "all" ||
        normalizeCategory(product.category) === categoryFilter)
    );
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

      <section className="product-card import-card">
       <h2>Enrich product dataset</h2>
       <p>
         Upload your input CSV and download the completed product catalog.
       </p>

        <form onSubmit={handleDatasetProcess}>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) =>
              setDatasetFile(event.target.files?.[0] || null)
            }
          />
          <button type="submit" disabled={datasetProcessing}>
            {datasetProcessing ? "Processing..." : "Enrich and Download"}
          </button>
        </form>

        {datasetStatus && <p>{datasetStatus}</p>}
      </section>

      <button
        type="button"
        className="export-button"
        onClick={handleCatalogExport}
      >
        Download Saved Catalog
      </button>

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

                  <ul>
                    {specifications.map((item, index) => (
                      <li key={`${item.key}-${index}`}>
                        <strong>{item.key}:</strong> {String(item.value)}
                      </li>
                    ))}
                  </ul>
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

  async function handleCatalogExport() {
    try {
      const response = await fetch(`${API_URL}/datasets/export-catalog`);

      if (!response.ok) {
        throw new Error("Catalog export failed.");
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = downloadUrl;
      link.download = "saved_catalog.csv";
      link.click();

      URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      setStatus(error.message);
    }
  }
}

export default App;