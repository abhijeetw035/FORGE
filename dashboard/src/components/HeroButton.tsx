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
      className="px-8 py-3 bg-zinc-100 hover:bg-zinc-300 text-black border border-zinc-200 transition font-medium rounded-md"
    >
      {isAuthenticated ? 'Go to Dashboard' : 'Get Started'}
    </button>
  );
}
