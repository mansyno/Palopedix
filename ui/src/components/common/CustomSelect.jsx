import React, { useState, useRef, useEffect, useMemo } from 'react';

export function CustomSelect({
  value = '',
  onChange,
  options = [],
  placeholder = 'Select...',
  searchable = false,
  disabled = false,
  accentColor = '#818cf8',
  style = {},
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef(null);
  const searchInputRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Focus search input when opened
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    }
    if (!isOpen) {
      setSearchQuery('');
    }
  }, [isOpen, searchable]);

  // Selected Option Object
  const selectedOption = useMemo(() => {
    return options.find(opt => String(opt.value) === String(value));
  }, [options, value]);

  // Filtered Options for search
  const filteredOptions = useMemo(() => {
    if (!searchable || !searchQuery.trim()) {
      return options;
    }
    const q = searchQuery.toLowerCase().trim();
    return options.filter(opt => (opt.label || opt.value || '').toLowerCase().includes(q));
  }, [options, searchable, searchQuery]);

  const handleSelect = (val) => {
    onChange(val);
    setIsOpen(false);
  };

  const isSelectedActive = value !== '' && value !== null && value !== undefined;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        userSelect: 'none',
        ...style,
      }}
    >
      {/* Trigger Button */}
      <div
        onClick={() => {
          if (!disabled) setIsOpen(prev => !prev);
        }}
        style={{
          width: '100%',
          fontSize: '0.78rem',
          padding: '0.32rem 0.5rem',
          background: 'rgba(15, 23, 42, 0.95)',
          border: isSelectedActive
            ? `1px solid ${accentColor}`
            : '1px solid var(--border-color)',
          borderRadius: '6px',
          color: isSelectedActive ? 'var(--text-primary)' : 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          boxShadow: isOpen ? `0 0 10px ${accentColor}40` : 'none',
          transition: 'all 0.15s ease',
          gap: '0.35rem',
          minHeight: '30px',
        }}
      >
        <span
          style={{
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            fontWeight: isSelectedActive ? 600 : 400,
          }}
        >
          {selectedOption ? selectedOption.label : placeholder}
        </span>

        <span
          style={{
            fontSize: '0.62rem',
            color: 'var(--text-secondary)',
            transform: isOpen ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.15s ease',
            flexShrink: 0,
          }}
        >
          ▼
        </span>
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            width: '100%',
            minWidth: '180px',
            background: 'rgba(11, 17, 33, 0.98)',
            border: '1px solid rgba(99, 102, 241, 0.4)',
            borderRadius: '8px',
            boxShadow: '0 15px 35px rgba(0, 0, 0, 0.85), 0 0 15px rgba(99, 102, 241, 0.2)',
            zIndex: 1500,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            backdropFilter: 'blur(16px)',
          }}
        >
          {/* Search Input (if searchable) */}
          {searchable && (
            <div style={{ padding: '0.35rem 0.45rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', background: 'rgba(0, 0, 0, 0.3)' }}>
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search..."
                style={{
                  width: '100%',
                  fontSize: '0.75rem',
                  padding: '0.25rem 0.4rem',
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  color: 'var(--text-primary)',
                  outline: 'none',
                }}
                onClick={e => e.stopPropagation()}
              />
            </div>
          )}

          {/* Options Scroll List */}
          <div
            style={{
              maxHeight: '240px',
              overflowY: 'auto',
              scrollbarWidth: 'thin',
              padding: '0.25rem 0',
            }}
          >
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => {
                const isSelected = String(opt.value) === String(value);
                return (
                  <div
                    key={String(opt.value)}
                    onClick={() => handleSelect(opt.value)}
                    style={{
                      padding: '0.35rem 0.6rem',
                      fontSize: '0.78rem',
                      color: isSelected ? 'var(--accent-gold)' : 'var(--text-primary)',
                      background: isSelected
                        ? 'rgba(99, 102, 241, 0.25)'
                        : 'transparent',
                      fontWeight: isSelected ? 700 : 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'background 0.1s ease',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {opt.label}
                    </span>
                    {isSelected && (
                      <span style={{ color: '#34d399', fontSize: '0.75rem', fontWeight: 900, marginLeft: '0.4rem' }}>
                        ✓
                      </span>
                    )}
                  </div>
                );
              })
            ) : (
              <div style={{ padding: '0.5rem', textAlign: 'center', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                No options found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default CustomSelect;
