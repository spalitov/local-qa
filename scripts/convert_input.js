#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function printUsage() {
  console.log('Usage: node scripts/convert-input.js --in <input.csv> [--out <output.json>]');
  console.log('Example: node scripts/convert-input.js --in examples/input.csv --out examples/audit-file.json');
}

function getArg(flag) {
  const args = process.argv.slice(2);
  const idx = args.indexOf(flag);
  if (idx < 0) return '';
  return args[idx + 1] || '';
}

function getStringValue(value) {
  if (value === null || value === undefined) return '';
  return String(value).normalize('NFKC');
}

function normalizeColumnKey(name) {
  return getStringValue(name)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

function getRowValue(row, candidates) {
  if (!row || typeof row !== 'object') return '';
  const entries = Object.entries(row);

  for (const key of candidates) {
    if (Object.prototype.hasOwnProperty.call(row, key)) {
      const value = getStringValue(row[key]);
      if (value.trim()) return value;
    }
  }

  for (const key of candidates) {
    const normalizedCandidate = normalizeColumnKey(key);
    for (const [rowKey, rowValue] of entries) {
      if (normalizeColumnKey(rowKey) === normalizedCandidate) {
        const value = getStringValue(rowValue);
        if (value.trim()) return value;
      }
    }
  }

  return '';
}

function parseJsonText(text) {
  const raw = getStringValue(text).trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function toArray(value) {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === 'object') return [value];
  return [];
}

function parseBool(value) {
  const raw = getStringValue(value).trim().toLowerCase();
  if (!raw) return false;
  return ['true', '1', 'yes', 'y'].includes(raw);
}

function uniqueTrimmedStrings(values) {
  const result = [];
  const seen = new Set();

  const list = Array.isArray(values) ? values : [values];
  for (const item of list) {
    const text = getStringValue(item).trim();
    if (!text || text === '{}' || text === '[]') continue;

    const key = text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(text);
  }

  return result;
}

function parseListLikeText(text) {
  const raw = getStringValue(text).trim();
  if (!raw || raw === '[]') return [];

  const parsed = parseJsonText(raw);
  if (parsed !== null) {
    if (Array.isArray(parsed)) return uniqueTrimmedStrings(parsed);
    if (typeof parsed === 'object') return uniqueTrimmedStrings(Object.values(parsed));
    return uniqueTrimmedStrings([parsed]);
  }

  const stripped = raw.replace(/^\[/, '').replace(/\]$/, '');
  return uniqueTrimmedStrings(
    stripped
      .split(/[\n\r,]+/)
      .map((part) => part.trim().replace(/^['"]|['"]$/g, ''))
      .filter(Boolean)
  );
}

function parseCompanyNotesToCategories(notesText) {
  const text = getStringValue(notesText).trim();
  if (!text) return {};

  const notes = {};
  let currentKey = 'important';
  notes[currentKey] = [];

  const lines = text.split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    if (line.startsWith('#')) {
      const heading = line.replace(/^#+/, '').trim().toLowerCase();
      const normalized = heading
        .replace(/&/g, 'and')
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
      currentKey = normalized || 'important';
      if (!notes[currentKey]) notes[currentKey] = [];
      continue;
    }

    let item = line;
    if (item.startsWith('\u2022') || item.startsWith('-')) item = item.slice(1).trim();
    if (item) notes[currentKey].push(item);
  }

  const clean = {};
  for (const [key, items] of Object.entries(notes)) {
    const unique = uniqueTrimmedStrings(items);
    if (unique.length) clean[key] = unique;
  }
  return clean;
}

function normalizeMessageType(typeRaw, agentId) {
  const value = getStringValue(typeRaw).trim().toLowerCase();
  if (!value) return agentId ? 'agent' : 'customer';
  if (['agent', 'assistant', 'support', 'csr', 'rep', 'outbound', 'outgoing'].includes(value)) {
    return 'agent';
  }
  if (['system', 'automation', 'bot'].includes(value)) return 'system';
  if (['inbound', 'incoming', 'customer', 'user', 'client'].includes(value)) return 'customer';
  return value;
}

function normalizeMessageMedia(media) {
  if (media === null || media === undefined) return [];
  const items = Array.isArray(media) ? media : [media];
  const urls = [];

  for (const item of items) {
    const raw = getStringValue(item).trim();
    if (!raw) continue;

    const parsed = parseJsonText(raw);
    if (Array.isArray(parsed)) {
      for (const parsedItem of parsed) {
        const maybe = getStringValue(parsedItem).trim();
        if (/^https?:\/\//i.test(maybe)) urls.push(maybe);
      }
      continue;
    }

    const matches = raw.match(/https?:\/\/[^\s<>"']+/gi);
    if (matches) urls.push(...matches.map((url) => url.trim()));
    else if (/^https?:\/\//i.test(raw)) urls.push(raw);
  }

  return urls;
}

function parseCsv(text) {
  const rows = [];
  const data = String(text || '').replace(/^\uFEFF/, '');
  const allRows = [];

  let current = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < data.length; i += 1) {
    const ch = data[i];
    const next = i + 1 < data.length ? data[i + 1] : '';

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      current.push(field);
      field = '';
    } else if (ch === '\n') {
      current.push(field);
      allRows.push(current);
      current = [];
      field = '';
    } else if (ch === '\r') {
      continue;
    } else {
      field += ch;
    }
  }

  if (field.length > 0 || current.length > 0) {
    current.push(field);
    allRows.push(current);
  }

  if (!allRows.length) return rows;

  const headers = allRows[0].map((h) => h.trim());
  for (let i = 1; i < allRows.length; i += 1) {
    const values = allRows[i];
    if (!values || values.every((v) => !getStringValue(v).trim())) continue;

    const row = {};
    for (let j = 0; j < headers.length; j += 1) {
      row[headers[j]] = values[j] || '';
    }
    rows.push(row);
  }

  return rows;
}

function resolveCliPath(value) {
  const raw = getStringValue(value).trim();
  if (!raw) return '';

  // On Windows, users may pass "/examples/file.json" expecting repo-relative output.
  if (process.platform === 'win32' && raw.startsWith('/') && !raw.startsWith('//')) {
    return path.resolve(raw.slice(1));
  }

  return path.resolve(raw);
}

function normalizePromotionRecord(input) {
  const title =
    getStringValue(input.title || input.name || input.promotion || input.coupon).trim() || 'Promotion';
  const content = [];

  const code = getStringValue(input.coupon || input.code).trim();
  const description = getStringValue(input.description || input.details).trim();
  const terms = getStringValue(input.terms || input.terms_and_conditions).trim();
  const starts = getStringValue(input.start_time || input.starts_at).trim();
  const ends = getStringValue(input.end_time || input.expires_at || input.expiration).trim();
  const link = getStringValue(input.link || input.url).trim();

  if (Array.isArray(input.content)) {
    input.content.forEach((line) => {
      const text = getStringValue(line).trim();
      if (text) content.push(text);
    });
  } else if (typeof input.content === 'string' && input.content.trim()) {
    input.content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .forEach((line) => content.push(line));
  }

  if (code) content.push(`Code: ${code}`);
  if (description) content.push(description);
  if (terms) content.push(`Terms: ${terms}`);
  if (starts) content.push(`Starts: ${starts}`);
  if (ends) content.push(`Ends: ${ends}`);
  if (link) content.push(`Link: ${link}`);

  const promotion = { title };
  if (content.length) promotion.content = content;

  const activeRaw = input.active_status || input.active || input.is_active;
  if (activeRaw !== undefined && getStringValue(activeRaw).trim()) {
    promotion.active_status = activeRaw;
  }

  return promotion;
}

function convertCsvRowToScenario(row) {
  const conversationRaw = getRowValue(row, ['CONVERSATION_JSON', 'CONVERSATION', 'MESSAGES_JSON', 'MESSAGES']);
  const conversationItems = toArray(parseJsonText(conversationRaw));
  const conversation = [];

  for (const msg of conversationItems) {
    if (!msg || typeof msg !== 'object') continue;

    const agentId = getStringValue(msg.agent || msg.agent_id || msg.agentId || msg.agentID).trim();
    const typeRaw = msg.message_type || msg.type || msg.role || msg.direction || msg.sender || msg.speaker;

    const entry = {
      message_media: normalizeMessageMedia(msg.message_media || msg.media || msg.attachments),
      message_text: getStringValue(msg.message_text || msg.text || msg.content || msg.body),
      message_type: normalizeMessageType(typeRaw, agentId),
    };

    if (agentId) entry.agent = agentId;

    const messageId = getStringValue(msg.message_id || msg.id).trim();
    if (messageId) entry.message_id = messageId;

    const dateTime = getStringValue(msg.date_time || msg.created_at || msg.timestamp).trim();
    if (dateTime) entry.date_time = dateTime;

    if (getStringValue(entry.message_text).trim()) conversation.push(entry);
  }

  const browsingHistoryRaw = getRowValue(row, [
    'LAST_5_PRODUCTS',
    'LAST5_PRODUCTS',
    'BROWSING_HISTORY',
    'RECENT_PRODUCTS',
  ]);
  const browsingHistoryItems = toArray(parseJsonText(browsingHistoryRaw));
  const browsingHistory = [];

  for (const itemRaw of browsingHistoryItems) {
    if (!itemRaw || typeof itemRaw !== 'object') continue;
    const name = getStringValue(itemRaw.product_name || itemRaw.name || itemRaw.product || itemRaw.title).trim();
    const link = getStringValue(itemRaw.product_link || itemRaw.link || itemRaw.url).trim();
    const viewDate = getStringValue(itemRaw.view_date || itemRaw.last_viewed || itemRaw.time_ago || itemRaw.viewed_at).trim();
    if (!name && !link) continue;

    const item = { item: name || link };
    if (link) item.link = link;
    if (viewDate) item.timeAgo = viewDate;
    browsingHistory.push(item);
  }

  const ordersRaw = getRowValue(row, ['ORDERS', 'ORDER_HISTORY', 'PAST_ORDERS']);
  const orderItems = toArray(parseJsonText(ordersRaw));
  const orders = [];

  for (const order of orderItems) {
    if (!order || typeof order !== 'object') continue;
    const productsForOrder = toArray(order.products || order.items || order.line_items);
    const items = [];

    for (const prod of productsForOrder) {
      if (!prod || typeof prod !== 'object') continue;

      const product = {
        name: getStringValue(prod.product_name || prod.name || prod.product || prod.title).trim(),
      };
      const price = prod.product_price || prod.price || prod.unit_price;
      const productLink = getStringValue(prod.product_link || prod.link || prod.url).trim();

      if (price !== undefined && getStringValue(price).trim()) product.price = price;
      if (productLink) product.productLink = productLink;
      if (product.name || product.price !== undefined || product.productLink) items.push(product);
    }

    const orderOut = {
      orderNumber: getStringValue(order.order_number || order.order_id || order.number).trim(),
      orderDate: getStringValue(order.order_date || order.date || order.created_at).trim(),
      items,
    };

    const orderLink = getStringValue(
      order.order_status_url || order.order_status_link || order.link || order.status_url || order.status_link
    ).trim();

    const trackingLink = getStringValue(
      order.order_tracking_link || order.tracking_link || order.tracking_url || order.order_tracking_url
    ).trim();

    if (orderLink) orderOut.link = orderLink;
    if (trackingLink) {
      orderOut.trackingLink = trackingLink;
      orderOut.order_tracking_link = trackingLink;
    }

    ['total', 'discount', 'coupon', 'created', 'created_at', 'date_time', 'email'].forEach((field) => {
      if (order[field] !== undefined && getStringValue(order[field]).trim()) {
        orderOut[field] = order[field];
      }
    });

    if (
      orderOut.orderNumber ||
      orderOut.orderDate ||
      orderOut.items.length ||
      orderOut.link ||
      orderOut.trackingLink ||
      orderOut.total ||
      orderOut.discount ||
      orderOut.coupon
    ) {
      orders.push(orderOut);
    }
  }

  const couponsRaw = getRowValue(row, ['COUPONS', 'CODES']);
  const couponItems = toArray(parseJsonText(couponsRaw));
  const coupons = [];

  for (const coupon of couponItems) {
    if (!coupon || typeof coupon !== 'object') continue;
    const couponOut = {};
    Object.entries(coupon).forEach(([key, value]) => {
      if (!getStringValue(key).trim()) return;
      if (value === undefined || value === null) return;
      if (typeof value === 'string' && !value.trim()) return;
      if (Array.isArray(value) && value.length === 0) return;
      couponOut[key] = value;
    });
    if (Object.keys(couponOut).length) coupons.push(couponOut);
  }

  const promotionsRaw = getRowValue(row, ['COMPANY_PROMOTIONS', 'PROMOTIONS', 'OFFERS']);
  const promotionsItems = toArray(parseJsonText(promotionsRaw));
  const promotions = [];

  for (const promotion of promotionsItems) {
    if (!promotion || typeof promotion !== 'object') continue;
    const normalized = normalizePromotionRecord(promotion);
    if (normalized.content && normalized.content.length) promotions.push(normalized);
  }

  const companyWebsite = getRowValue(row, ['COMPANY_WEBSITE', 'WEBSITE', 'SITE_URL']).trim();
  const rightPanel = {
    source: {
      label: 'Website',
      value: companyWebsite,
      date: '',
    },
  };

  if (browsingHistory.length) rightPanel.browsingHistory = browsingHistory;
  if (orders.length) rightPanel.orders = orders;
  if (coupons.length) rightPanel.coupons = coupons;
  if (promotions.length) rightPanel.promotions = promotions;

  const notesText = getRowValue(row, ['COMPANY_NOTES', 'NOTES', 'GUIDELINES', 'INTERNAL_NOTES']);
  const scenario = {
    id: getRowValue(row, ['SEND_ID', 'SCENARIO_ID', 'ID']).trim(),
    companyName: getRowValue(row, ['COMPANY_NAME', 'BRAND', 'COMPANY']).trim(),
    companyWebsite,
    agentName: getRowValue(row, ['PERSONA', 'AGENT_NAME', 'AGENT']).trim(),
    messageTone: getRowValue(row, ['MESSAGE_TONE', 'TONE']).trim(),
    conversation,
    notes: parseCompanyNotesToCategories(notesText),
    rightPanel,
    escalation_preferences: parseListLikeText(
      getRowValue(row, ['ESCALATION_TOPICS', 'ESCALATION_PREFERENCES', 'ESCALATIONS'])
    ),
    blocklisted_words: parseListLikeText(
      getRowValue(row, ['BLOCKLISTED_WORDS', 'BLOCKLIST_WORDS', 'BLOCKLIST', 'BLOCKED_WORDS'])
    ),
  };

  const hasShopifyRaw = getRowValue(row, ['HAS_SHOPIFY', 'SHOPIFY', 'HAS_SHOPIFY_STORE']);
  if (hasShopifyRaw.trim()) scenario.has_shopify = parseBool(hasShopifyRaw);

  return scenario;
}

function run() {
  const showHelp = process.argv.includes('--help') || process.argv.includes('-h');
  const inputArg = getArg('--in') || getArg('-i');
  const outputArg = getArg('--out') || getArg('-o');

  if (showHelp || !inputArg) {
    printUsage();
    process.exit(showHelp ? 0 : 1);
  }

  const inputPath = resolveCliPath(inputArg);
  const outputPath = outputArg ? resolveCliPath(outputArg) : '';

  if (!fs.existsSync(inputPath)) {
    console.error(`CSV file not found: ${inputPath}`);
    process.exit(1);
  }

  const rows = parseCsv(fs.readFileSync(inputPath, 'utf8'));
  if (!rows.length) {
    console.error('CSV has no data rows.');
    process.exit(1);
  }

  const scenarios = [];
  let skippedRows = 0;

  rows.forEach((row) => {
    const scenario = convertCsvRowToScenario(row);
    if (!scenario.id || !scenario.companyName) {
      skippedRows += 1;
      return;
    }
    scenarios.push(scenario);
  });

  if (!scenarios.length) {
    console.error('No valid scenarios produced. Required columns: SEND_ID and COMPANY_NAME.');
    process.exit(1);
  }

  const payload = { scenarios };
  const outputJson = `${JSON.stringify(payload, null, 2)}\n`;

  if (outputPath) {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, outputJson, 'utf8');
    console.log(`Wrote ${scenarios.length} scenarios to ${outputPath}`);
  } else {
    process.stdout.write(outputJson);
  }

  if (skippedRows > 0) {
    console.error(`Skipped ${skippedRows} row(s) missing SEND_ID or COMPANY_NAME.`);
  }
}

run();
