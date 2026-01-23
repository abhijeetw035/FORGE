'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { register as registerUser, login } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { login: authLogin } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true);
      setError('');
      
      await registerUser(data.email, data.password);
      
      const response = await login(data.email, data.password);
      await authLogin(response.access_token);
      
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo / Title */}
        <div className="text-center mb-8 animate-in fade-in slide-in-from-top-4 duration-700">
          <h1 className="text-4xl font-bold text-zinc-50 mb-2 tracking-tight">
            FORGE
          </h1>
          <p className="text-zinc-400">
            Create your account to get started
          </p>
        </div>

        {/* Register Card */}
        <div className="bg-zinc-950/40 backdrop-blur-md rounded-md border border-zinc-800/50 shadow-2xl p-8 hover:shadow-zinc-900/50 transition-all duration-300">
          <h2 className="text-2xl font-bold text-zinc-50 mb-6">
            Sign Up
          </h2>

          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-950/50 border border-red-800">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-zinc-300 mb-2"
              >
                Email
              </label>
              <input
                {...register('email')}
                type="email"
                id="email"
                className="w-full px-4 py-2 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-50 focus:ring-2 focus:ring-zinc-100 focus:border-transparent transition placeholder:text-zinc-600"
                placeholder="you@example.com"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-400">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-zinc-300 mb-2"
              >
                Password
              </label>
              <input
                {...register('password')}
                type="password"
                id="password"
                className="w-full px-4 py-2 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-50 focus:ring-2 focus:ring-zinc-100 focus:border-transparent transition placeholder:text-zinc-600"
                placeholder="••••••••"
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-400">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-zinc-300 mb-2"
              >
                Confirm Password
              </label>
              <input
                {...register('confirmPassword')}
                type="password"
                id="confirmPassword"
                className="w-full px-4 py-2 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-50 focus:ring-2 focus:ring-zinc-100 focus:border-transparent transition placeholder:text-zinc-600"
                placeholder="••••••••"
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-400">
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-primary hover:bg-primary-hover text-white font-medium rounded-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Creating account...' : 'Sign Up'}
            </button>
          </form>

          {/* Sign In Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-zinc-400">
              Already have an account?{' '}
              <Link
                href="/login"
                className="text-zinc-50 hover:underline font-medium"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>

        {/* Back to Home */}
        <div className="mt-6 text-center">
          <Link
            href="/"
            className="text-sm text-zinc-400 hover:text-zinc-50 transition"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
