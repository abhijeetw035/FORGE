'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

export default function HeroButton() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  const handleClick = () => {
    if (isAuthenticated) {
      router.push('/dashboard');
    } else {
      router.push('/register');
    }
  };

  return (
    <button
      onClick={handleClick}
      className="px-8 py-3 bg-primary bg-zinc-100 hover:bg-primary-hover text-black rounded-md text-lg shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer hover:scale-105 active:scale-95"
    >
      {isAuthenticated ? 'Go to Dashboard' : 'Get Started'}
    </button>
  );
}
