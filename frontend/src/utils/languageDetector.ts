/**
 * Визначає мову на основі телефонного номера
 */
export const detectLanguageFromPhone = (phoneNumber: string): string => {
  // Видаляємо всі символи крім цифр та +
  const cleanPhone = phoneNumber.replace(/[^\d+]/g, "");

  // Визначаємо країну за кодом
  if (cleanPhone.startsWith("+48") || cleanPhone.startsWith("48")) {
    return "pl"; // Польща
  }
  if (cleanPhone.startsWith("+380") || cleanPhone.startsWith("380")) {
    return "uk"; // Україна
  }
  if (cleanPhone.startsWith("+44") || cleanPhone.startsWith("44")) {
    return "en"; // Великобританія
  }
  if (cleanPhone.startsWith("+1")) {
    return "en"; // США/Канада
  }
  if (cleanPhone.startsWith("+49") || cleanPhone.startsWith("49")) {
    return "de"; // Німеччина
  }
  if (cleanPhone.startsWith("+33") || cleanPhone.startsWith("33")) {
    return "fr"; // Франція
  }
  if (cleanPhone.startsWith("+34") || cleanPhone.startsWith("34")) {
    return "es"; // Іспанія
  }
  if (cleanPhone.startsWith("+39") || cleanPhone.startsWith("39")) {
    return "it"; // Італія
  }

  // За замовчуванням повертаємо польську
  return "pl";
};

/**
 * Список доступних мов
 */
export const AVAILABLE_LANGUAGES = [
  { code: "pl", name: "Polski", flag: "🇵🇱" },
  { code: "uk", name: "Українська", flag: "🇺🇦" },
  { code: "en", name: "English", flag: "🇬🇧" },
  { code: "de", name: "Deutsch", flag: "🇩🇪" },
  { code: "fr", name: "Français", flag: "🇫🇷" },
  { code: "es", name: "Español", flag: "🇪🇸" },
  { code: "it", name: "Italiano", flag: "🇮🇹" },
];

/**
 * Отримати назву мови за кодом
 */
export const getLanguageName = (code: string): string => {
  const lang = AVAILABLE_LANGUAGES.find((l) => l.code === code);
  return lang ? `${lang.flag} ${lang.name}` : code.toUpperCase();
};
