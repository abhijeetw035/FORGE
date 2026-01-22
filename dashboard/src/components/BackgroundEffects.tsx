'use client';

export default function BackgroundEffects() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
      {/* Matrix Data Streams - More vertical lines at different positions */}
      <div 
        className="absolute w-[1px] h-64 bg-gradient-to-b from-transparent via-cyan-500/40 to-transparent"
        style={{
          left: '10%',
          animation: 'float-up 15s linear infinite',
          animationDelay: '0s',
        }}
      />
      <div 
        className="absolute w-[1px] h-48 bg-gradient-to-b from-transparent via-blue-500/40 to-transparent"
        style={{
          left: '30%',
          animation: 'float-up 12s linear infinite',
          animationDelay: '2s',
        }}
      />
      <div 
        className="absolute w-[1px] h-56 bg-gradient-to-b from-transparent via-violet-500/40 to-transparent"
        style={{
          left: '50%',
          animation: 'float-up 18s linear infinite',
          animationDelay: '4s',
        }}
      />
      <div 
        className="absolute w-[1px] h-40 bg-gradient-to-b from-transparent via-cyan-500/40 to-transparent"
        style={{
          left: '70%',
          animation: 'float-up 14s linear infinite',
          animationDelay: '6s',
        }}
      />
      <div 
        className="absolute w-[1px] h-52 bg-gradient-to-b from-transparent via-blue-500/40 to-transparent"
        style={{
          left: '90%',
          animation: 'float-up 16s linear infinite',
          animationDelay: '8s',
        }}
      />

      {/* Pulse Orbs - Giant blurred circles that slowly pulse */}
      <div 
        className="absolute w-[600px] h-[600px] rounded-full bg-cyan-600/5 blur-3xl"
        style={{
          top: '5%',
          left: '5%',
          animation: 'pulse-slow 7s ease-in-out infinite',
        }}
      />
      <div 
        className="absolute w-[500px] h-[500px] rounded-full bg-violet-600/5 blur-3xl"
        style={{
          bottom: '10%',
          right: '10%',
          animation: 'pulse-slow 9s ease-in-out infinite',
          animationDelay: '3s',
        }}
      />
    </div>
  );
}
