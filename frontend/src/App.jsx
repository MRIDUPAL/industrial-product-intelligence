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

function App() {
  const [products, setProducts] = useState([]);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

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

  return (
    <main className="dashboard">
      <header>
        <p className="eyebrow">Industrial Product Intelligence</p>
        <h1>Product catalog</h1>
        <p className="subtitle">
          Extract, enrich, and trace industrial product information.
        </p>
      </header>

      <section className="product-card">
        <h2>Import product PDF</h2>

        <form onSubmit={handleImport}>
          <input
            type="file"
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files[0])}
          />
          <button type="submit">Import PDF</button>
        </form>

        {status && <p>{status}</p>}
      </section>

      {loading ? (
        <p>Loading products...</p>
      ) : (
        <section className="product-grid">
          {products.map((product) => {
            const technicalEvidence = (product.evidence || []).filter(
              (item) =>
                !hiddenEvidenceFields.includes(
                  item.field_name.toLowerCase()
                )
            );

            return (
              <article className="product-card" key={product.id}>
                <span className="category">
                  {product.category || "Uncategorized"}
                </span>

                <h2>{product.name}</h2>

                <p className="brand">
                  {product.brand} · {product.model}
                </p>

                <p>
                  {product.description || "No description available."}
                </p>

                <details>
                  <summary>
                    Specifications ({Object.keys(product.specifications || {}).length})
                  </summary>

                  <ul>
                    {Object.entries(product.specifications || {}).map(
                      ([key, value]) => (
                        <li key={key}>
                          <strong>{key}:</strong> {String(value)}
                        </li>
                      )
                    )}
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
                          <br />
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            View source
                          </a>
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