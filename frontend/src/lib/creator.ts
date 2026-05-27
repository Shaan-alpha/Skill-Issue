// The project creator's GitHub login. Their own profile gets the golden
// "creator" treatment (results page + shareable card). Single source of truth.
export const CREATOR_LOGIN = "shaan-alpha";

export function isCreator(username: string): boolean {
  return username.toLowerCase() === CREATOR_LOGIN;
}
