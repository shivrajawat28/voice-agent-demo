/**
 * Timezone Utility for FertoBot Voice Agent Frontend
 * Converts UTC or ISO timestamps to Asia/Kolkata (IST, UTC+05:30) 12-hour format with AM/PM.
 */

export function formatToIST(
  dateOrIso: string | Date | number | null | undefined,
  includeDate: boolean = true
): string {
  if (!dateOrIso) {
    return '';
  }

  const d = typeof dateOrIso === 'string' || typeof dateOrIso === 'number'
    ? new Date(dateOrIso)
    : dateOrIso;

  if (isNaN(d.getTime())) {
    return String(dateOrIso);
  }

  // Format using Intl.DateTimeFormat with Asia/Kolkata timezone
  const timeOptions: Intl.DateTimeFormatOptions = {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  };

  const timePart = new Intl.DateTimeFormat('en-IN', timeOptions).format(d);

  if (!includeDate) {
    return `${timePart} IST`;
  }

  const dateOptions: Intl.DateTimeFormatOptions = {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  };

  const datePart = new Intl.DateTimeFormat('en-IN', dateOptions).format(d);
  return `${datePart}, ${timePart} IST`;
}
