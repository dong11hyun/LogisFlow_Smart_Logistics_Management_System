-- =================================================================
-- Git V1.0 - Logis-Flow ?¥?‡ë¦? ï¿½ë’ªï¿½ê¶ï§ï¿½ (PostgreSQL è¹‚ï¿½ï¿½ì†š)
-- =================================================================

-- 1. ??¨ì¢‰ì»¼ï¿½ê¶? ï¿½ì ™è¹‚ï¿½ ï¿½ë?’ï¿½?” ?‡‰ï¿?
CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY, -- AUTO_INCREMENT ï¿½ï¿½ï¿½ï¿½?–Š SERIAL ï¿½ê¶—ï¿½ìŠœ
    company_name VARCHAR(100) NOT NULL
);

-- 2. ï§¡ì„??? ï¿½ì ™è¹‚ï¿½ ï¿½ë?’ï¿½?” ?‡‰ï¿?
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    warehouse_name VARCHAR(100) NOT NULL,
    address VARCHAR(255)
);

-- 3. ï¿½ê¸½ï¿½ë?? ï§ë‰?’ªï¿½ê½£ ï¿½ì ™è¹‚ï¿½ ï¿½ë?’ï¿½?” ?‡‰ï¿?
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL
);

-- 4. ï¿½ì†•?‡¾ï¿? ï¿½ì ™è¹‚ï¿½ ï¿½ë?’ï¿½?” ?‡‰ï¿? (Shipment)
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    company_id INT,
    origin_warehouse_id INT,
    destination_warehouse_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (company_id),
    FOREIGN KEY (origin_warehouse_id) REFERENCES warehouses (warehouse_id),
    FOREIGN KEY (destination_warehouse_id) REFERENCES warehouses (warehouse_id)
);

-- 5. ï¿½ì†•?‡¾ï¿?-ï¿½ê¸½ï¿½ë?? ï¿½ë–ï¿½ï¿½ï¿½ï¿½?– ?„¿ï¿½æ?¨ï¿½ ï¿½ë?’ï¿½?” ?‡‰ï¿? (Shipment Items)
-- ï¿½ë¿¬æ¹²ï¿½ AUTO_INCREMENTåª›ï¿½ ï¿½ë¾¾ï¿½ì‘èª˜ï¿½æ¿¡ï¿½ å«„ê³—?“½ ï¿½ë‹”ï¿½ì ™ï¿½ë¸· å¯ƒï¿½ ï¿½ë¾¾ï¿½ë’¿ï¿½ë•²ï¿½ë–.
CREATE TABLE shipment_items (
    shipment_id INT,
    product_id INT,
    quantity INT NOT NULL,
    PRIMARY KEY (shipment_id, product_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

-- 6. ï¿½ì†•?‡¾ï¿? ï¿½ê¸½ï¿½ê¹­ è¹‚ï¿½å¯ƒï¿½ æ¿¡ì’“? ‡ ï¿½ë?’ï¿½?” ?‡‰ï¿? (Shipment Updates)
CREATE TABLE shipment_updates (
    update_id SERIAL PRIMARY KEY,
    shipment_id INT,
    status_code VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    timestamp TIMESTAMP NOT NULL, -- DATETIME ï¿½ï¿½ï¿½ï¿½?–Š TIMESTAMP ï¿½ê¶—ï¿½ìŠœ
    FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id)
);

-- 7. ï¿½ê½¦ï¿½ë’« ?ºê¾©ê½ï¿½ì“£ ï¿½ìï¿½ë¸³ ï¿½ë¸˜ï¿½ë‹” ï¿½ì”¤ï¿½ëœ³ï¿½ë’ª
CREATE INDEX idx_shipment_updates_shipment_id_timestamp ON shipment_updates (shipment_id, timestamp);