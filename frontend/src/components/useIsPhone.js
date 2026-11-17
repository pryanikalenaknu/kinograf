import { useEffect, useState } from 'react';

const PHONE_QUERY = '(max-width: 767px)';

/** Повертає `true`, коли ширина вікна менша за межу мобільної версії (768 px). */
export function useIsPhone() {
  const [isPhone, setIsPhone] = useState(() => window.matchMedia(PHONE_QUERY).matches);

  useEffect(() => {
    const media = window.matchMedia(PHONE_QUERY);
    const update = () => setIsPhone(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  return isPhone;
}
