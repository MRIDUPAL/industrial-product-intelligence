import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProducts() {
      try {
        const response = await fetch(`${API_URL}/products`);

        if (!response.ok) {
          throw new Error("Could not load products");
        }

        const productData = await response.json();

        const productsWithEvidence = await Promise.all(
          productData.map(async (product) => {
            const evidenceResponse = await fetch(
              `${API_URL}/products/${product.id}/evidence`
            );

            const evidence = evidenceResponse.ok
              ? await evidenceResponse.json()
              : [];

            return { ...product, evidence };
          })
        );

        setProducts(productsWithEvidence);
      } catch (error) {
        setError(error.message);
      } finally {
        setLoading(false);
      }
    }

    loadProducts();
  }, []);

  return (
    <main className="dashboard">
      <header>
        <p className="eyebrow">Industrial Product Intelligence</p>
        <h1>Product catalog</h1>
        <p className="subtitle">
          Structured products and traceable source information.
        </p>
      </header>

      {loading && <p>Loading products...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && (
        <section className="product-grid">
          {products.map((product) => (
            <article className="product-card" key={product.id}>
              <span className="category">{product.category || "Uncategorized"}</span>
              <h2>{product.name}</h2>
              <p className="brand">
                {product.brand} · {product.model}
              </p>
              <p>{product.description || "No description available."}</p>

              <h3>Specifications</h3>
              <ul>
                {Object.entries(product.specifications || {}).map(
                  ([key, value]) => (
                    <li key={key}>
                      <strong>{key}:</strong> {String(value)}
                    </li>
                  )
                )}
              </ul>
              <h3>Evidence</h3>

              {product.evidence?.length ? (
                <ul>
                  {product.evidence.map((item) => (
                    <li key={item.id}>
                      <strong>{item.field_name}:</strong> {item.value}
                      <br />
                      <a href={item.source_url} target="_blank" rel="noreferrer">
                        View source
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No evidence recorded.</p>
              )}
            </article>
          ))}
        </section>
      )}
    </main>
  );
}

export default App;