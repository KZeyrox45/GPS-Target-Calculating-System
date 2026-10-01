export default function formatApiError(status, detail) {
  if (typeof detail === 'string' && detail.length > 0) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        const field = item.loc && item.loc.length > 1 ? item.loc[item.loc.length - 1] : null;
        const msg = item.msg || 'invalid value';
        return field ? `${field}: ${msg}` : msg;
      })
      .join('; ');
  }
  return `Failed to process request (HTTP ${status})`;
}