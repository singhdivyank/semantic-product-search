INSERT_REVIEWS_TEMPLATE = """
    INSERT INTO reviews (
        parent_asin, asin, user_id, rating, title, review_text,
        helpful_vote, verified_purchase, timestamp_raw, reviewed_at,
        sentiment_label, sentiment_score
    ) VALUES (
        :parent_asin, :asin, :user_id, :rating, :title, :review_text,
        :helpful_vote, :verified_purchase, :timestamp_raw, :reviewed_at,
        :sentiment_label, :sentiment_score
    )
    ON CONFLICT DO NOTHING
""".strip()

SELECT_PARENT_ASINS = "SELECT parent_asin FROM products"

UPSERT_PRODUCT_TEMPLATE = """
    INSERT INTO products (
        parent_asin, title, subtitle, author, main_category, store,
        average_rating, rating_number, price_raw, price,
        features, description, categories, details,
        images, videos, bought_together
    ) VALUES (
        :parent_asin, :title, :subtitle, :author, :main_category, :store,
        :average_rating, :rating_number, :price_raw, :price,
        :features::jsonb, :description::jsonb, :categories::jsonb,
        :details::jsonb, :images::jsonb, :videos::jsonb,
        :bought_together::jsonb
    )
    ON CONFLICT (parent_asin) DO UPDATE SET
        title           = EXCLUDED.title,
        average_rating  = EXCLUDED.average_rating,
        rating_number   = EXCLUDED.rating_number,
        price_raw       = EXCLUDED.price_raw,
        price           = EXCLUDED.price,
        features        = EXCLUDED.features,
        description     = EXCLUDED.description,
        categories      = EXCLUDED.categories,
        details         = EXCLUDED.details,
        images          = EXCLUDED.images,
        videos          = EXCLUDED.videos,
        bought_together = EXCLUDED.bought_together,
        ingested_at     = NOW()
""".strip()

UPSERT_EMBED_TEMPLATE = """
    INSERT INTO product_embeddings (
        parent_asin, embedding, embedding_half, model_name, mlflow_run_id
    ) VALUES (
        :parent_asin,
        :embedding::vector,
        :embedding_half::halfvec,
        :model_name,
        :mlflow_run_id
    )
    ON CONFLICT (parent_asin) DO UPDATE SET
        embedding      = EXCLUDED.embedding,
        embedding_half = EXCLUDED.embedding_half,
        model_name     = EXCLUDED.model_name,
        mlflow_run_id  = EXCLUDED.mlflow_run_id,
        ingested_at    = NOW()
""".strip()
