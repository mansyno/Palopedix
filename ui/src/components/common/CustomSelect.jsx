import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';

export function CustomSelect({
  value = '',
  onChange,
  options = [],
  placeholder = 'Select...',
  searchable = false,
  disabled = false,
  accentColor = '#818cf8',
  style = {},
  renderOption = null,
  renderSelected = null,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [floatingStyle, setFloatingStyle] = useState({});
  const containerRef = useRef(null);
  const floatingMenuRef = useRef(null);
  const searchInputRef = useRef(null);

  // Viewport-aware position calculator (prevents truncation & handles auto-flip)
  const updatePosition = useCallback(() => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const vWidth = window.innerWidth;
    const vHeight = window.innerHeight;

    // Target width: match trigger button width, but at least 220px
    const menuWidth = Math.max(rect.width, 220);

    // Horizontal positioning: align with trigger left, clamp inside viewport margins
    let left = rect.left;
    if (left + menuWidth > vWidth - 10) {
      left = Math.max(10, vWidth - menuWidth - 10);
    }
    if (left < 10) left = 10;

    // Available vertical clearances
    const spaceBelow = vHeight - rect.bottom - 10;
    const spaceAbove = rect.top - 10;
    const maxDesiredHeight = 280;

    let top;
    let maxContentHeight;

    if (spaceBelow < 220 && spaceAbove > spaceBelow) {
      // Open UPWARD
      const available = Math.min(maxDesiredHeight, spaceAbove);
      top = rect.top - available - 4;
      maxContentHeight = available;
    } else {
      // Open DOWNWARD
      top = rect.bottom + 4;
      maxContentHeight = Math.min(maxDesiredHeight, spaceBelow);
    }

    setFloatingStyle({
      position: 'fixed',
      top: `${Math.round(top)}px`,
      left: `${Math.round(left)}px`,
      width: `${Math.round(menuWidth)}px`,
      maxHeight: `${Math.round(maxContentHeight)}px`,
      zIndex: 999999,
    });
  }, []);

  // Update floating position on open, scroll, or resize
  useEffect(() => {
    if (!isOpen) return;
    updatePosition();

    const handleScroll = () => {
      updatePosition();
    };
    const handleResize = () => {
      updatePosition();
    };

    window.addEventListener('scroll', handleScroll, true);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('scroll', handleScroll, true);
      window.removeEventListener('resize', handleResize);
    };
  }, [isOpen, updatePosition]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      const isInsideContainer = containerRef.current && containerRef.current.contains(e.target);
      const isInsideFloating = floatingMenuRef.current && floatingMenuRef.current.contains(e.target);
      if (!isInsideContainer && !isInsideFloating) {
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
          fontSize: '0.84rem',
          padding: '0.3rem 0.6rem',
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
          minHeight: '34px',
        }}
      >
        <div
          style={{
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            fontWeight: isSelectedActive ? 600 : 400,
            display: 'flex',
            alignItems: 'center',
            minWidth: 0,
            flexGrow: 1,
          }}
        >
          {selectedOption
            ? (renderSelected ? renderSelected(selectedOption) : selectedOption.label)
            : placeholder}
        </div>

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

      {/* Floating Dropdown Menu (Portaled to document.body to prevent any container clipping or scrollbars) */}
      {isOpen && createPortal(
        <div
          ref={floatingMenuRef}
          style={{
            ...floatingStyle,
            background: 'rgba(11, 17, 33, 0.98)',
            border: '1px solid rgba(99, 102, 241, 0.4)',
            borderRadius: '8px',
            boxShadow: '0 15px 35px rgba(0, 0, 0, 0.85), 0 0 15px rgba(99, 102, 241, 0.2)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            backdropFilter: 'blur(16px)',
            boxSizing: 'border-box',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input (if searchable) */}
          {searchable && (
            <div style={{ padding: '0.35rem 0.45rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', background: 'rgba(0, 0, 0, 0.3)', flexShrink: 0 }}>
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
                  boxSizing: 'border-box',
                }}
                onClick={e => e.stopPropagation()}
              />
            </div>
          )}

          {/* Options Scroll List */}
          <div
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              scrollbarWidth: 'thin',
              padding: '2px 0',
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
                      padding: '0.15rem 0.6rem',
                      fontSize: '0.82rem',
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
                      gap: '0.4rem',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', minWidth: 0, flexGrow: 1 }}>
                      {renderOption ? renderOption(opt, isSelected) : (
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {opt.label}
                        </span>
                      )}
                    </div>
                    {isSelected && (
                      <span style={{ color: '#34d399', fontSize: '0.75rem', fontWeight: 900, marginLeft: '0.4rem', flexShrink: 0 }}>
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
        </div>,
        document.body
      )}
    </div>
  );
}

export default CustomSelect;
