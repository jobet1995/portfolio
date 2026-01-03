(function($, window, document, undefined){
  "use strict";

  // Enhanced Utility class with more features
  class Utility {
    static ajaxPost(url, data, successCallback, errorCallback) {
      $.ajax({
        url: url,
        method: 'POST',
        data: data,
        headers: {'X-CSRFToken': Utility.getCSRFToken()},
        dataType: 'json',
        timeout: 10000 // 10 second timeout
      }).done(successCallback)
        .fail(errorCallback || function(xhr){ 
          Utility.logError('AJAX request failed', {
            url: url,
            status: xhr.status,
            statusText: xhr.statusText
          });
        });
    }

    static ajaxGet(url, successCallback, errorCallback) {
      $.ajax({
        url: url,
        method: 'GET',
        dataType: 'json',
        timeout: 10000
      }).done(successCallback)
        .fail(errorCallback || function(xhr){ 
          Utility.logError('AJAX GET request failed', {
            url: url,
            status: xhr.status,
            statusText: xhr.statusText
          });
        });
    }

    static getCSRFToken() {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
             document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    static logError(message, data) {
      console.error(`[Portfolio Error] ${message}`, data || '');
      // You could also send errors to a logging service here
    }

    static logInfo(message, data) {
      console.info(`[Portfolio Info] ${message}`, data || '');
    }

    static debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    }

    static throttle(func, limit) {
      let inThrottle;
      return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
          func.apply(context, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    }

    static isValidEmail(email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(email);
    }

    static isValidPhone(phone) {
      const phoneRegex = /^[+]?[\d\s\-\(\)]+$/;
      return phoneRegex.test(phone) && phone.replace(/\D/g, '').length >= 10;
    }

    static sanitizeInput(input) {
      const div = document.createElement('div');
      div.textContent = input;
      return div.innerHTML;
    }

    static getViewportWidth() {
      return Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    }

    static getViewportHeight() {
      return Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
    }

    static isElementInViewport(el) {
      const rect = el.getBoundingClientRect();
      return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
      );
    }
  }

  // Enhanced ContactFormManager with better validation and accessibility
  class ContactFormManager {
    constructor(formSelector) {
      this.$form = $(formSelector);
      this.$messageContainer = $('<div class="form-message" role="alert" aria-live="polite"></div>').insertBefore(this.$form);
      this.$submitBtn = this.$form.find('button[type="submit"]');
      this.originalBtnText = this.$submitBtn.text();
      this.isSubmitting = false;
      this.init();
    }

    init() {
      this.$form.on('submit', (e) => {
        e.preventDefault();
        if (!this.isSubmitting && this.validate()) {
          this.submitForm();
        }
      });

      // Real-time validation feedback
      this.$form.find('input, textarea').on('blur', (e) => {
        this.validateField($(e.currentTarget));
      });

      // Clear error on input
      this.$form.find('input, textarea').on('input', (e) => {
        $(e.currentTarget).removeClass('input-error');
        this.clearFieldError($(e.currentTarget));
      });
    }

    validateField($field) {
      const fieldType = $field.attr('type');
      const value = $field.val().trim();
      const isRequired = $field.prop('required');
      let isValid = true;
      let errorMessage = '';

      if (isRequired && !value) {
        isValid = false;
        errorMessage = 'This field is required';
      } else if (value) {
        switch (fieldType) {
          case 'email':
            if (!Utility.isValidEmail(value)) {
              isValid = false;
              errorMessage = 'Please enter a valid email address';
            }
            break;
          case 'tel':
            if (!Utility.isValidPhone(value)) {
              isValid = false;
              errorMessage = 'Please enter a valid phone number';
            }
            break;
        }

        // Length validation
        const minLength = $field.attr('minlength');
        const maxLength = $field.attr('maxlength');
        
        if (minLength && value.length < parseInt(minLength)) {
          isValid = false;
          errorMessage = `Minimum ${minLength} characters required`;
        }
        
        if (maxLength && value.length > parseInt(maxLength)) {
          isValid = false;
          errorMessage = `Maximum ${maxLength} characters allowed`;
        }
      }

      if (!isValid) {
        $field.addClass('input-error');
        this.showFieldError($field, errorMessage);
      } else {
        $field.removeClass('input-error');
        this.clearFieldError($field);
      }

      return isValid;
    }

    showFieldError($field, message) {
      this.clearFieldError($field);
      const $error = $('<span class="field-error" role="alert"></span>').text(message);
      $field.after($error);
    }

    clearFieldError($field) {
      $field.siblings('.field-error').remove();
    }

    validate() {
      let valid = true;
      this.$form.find('input, textarea').each((index, element) => {
        const $element = $(element);
        if (!this.validateField($element)) {
          valid = false;
        }
      });
      return valid;
    }

    submitForm() {
      this.isSubmitting = true;
      this.setSubmitButtonState('Sending...', true);
      
      const url = this.$form.attr('action');
      const data = this.$form.serialize();
      
      Utility.ajaxPost(url, data, (response) => {
        this.handleSuccess(response);
      }, (xhr) => {
        this.handleError(xhr);
      }).always(() => {
        this.isSubmitting = false;
        this.setSubmitButtonState(this.originalBtnText, false);
      });
    }

    handleSuccess(response) {
      if (response.success) {
        this.showMessage('Thank you! Your message has been sent successfully.', 'success');
        this.$form[0].reset();
        // Track successful form submission if analytics is available
        if (typeof gtag !== 'undefined') {
          gtag('event', 'form_submit', {
            'event_category': 'Contact',
            'event_label': 'Contact Form'
          });
        }
      } else {
        this.showMessage(response.error || 'An error occurred while sending your message.', 'error');
      }
    }

    handleError(xhr) {
      let errorMessage = 'Server error. Please try again later.';
      
      if (xhr.status === 429) {
        errorMessage = 'Too many requests. Please wait before trying again.';
      } else if (xhr.status === 413) {
        errorMessage = 'File too large. Please reduce the file size.';
      } else if (xhr.status >= 500) {
        errorMessage = 'Server is temporarily unavailable. Please try again later.';
      }
      
      this.showMessage(errorMessage, 'error');
      Utility.logError('Form submission failed', { status: xhr.status, response: xhr.responseText });
    }

    setSubmitButtonState(text, disabled) {
      this.$submitBtn.text(text).prop('disabled', disabled);
      if (disabled) {
        this.$submitBtn.addClass('loading');
      } else {
        this.$submitBtn.removeClass('loading');
      }
    }

    showMessage(message, type) {
      this.$messageContainer
        .removeClass('success error warning')
        .addClass(type)
        .text(message)
        .fadeIn()
        .delay(5000)
        .fadeOut(() => {
          this.$messageContainer.removeClass('success error warning');
        });
    }
  }

  // Enhanced SmoothScrollManager with better accessibility and performance
  class SmoothScrollManager {
    constructor(anchorSelector, offset = 0, duration = 600) {
      this.anchorSelector = anchorSelector;
      this.offset = offset;
      this.duration = duration;
      this.init();
    }

    init() {
      $(document).on('click', this.anchorSelector, (e) => {
        const href = e.currentTarget.getAttribute('href');
        const target = $(href);
        
        if (target.length && href.startsWith('#')) {
          e.preventDefault();
          this.smoothScrollTo(target);
          
          // Update focus for accessibility
          setTimeout(() => {
            target.attr('tabindex', '-1');
            target[0].focus();
          }, this.duration);
          
          // Update URL without page jump
          if (history.pushState) {
            history.pushState(null, null, href);
          }
        }
      });
    }

    smoothScrollTo(target) {
      const targetTop = target.offset().top - this.offset;
      const start = window.pageYOffset;
      const distance = targetTop - start;
      let startTime = null;

      function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const run = easeInOutQuad(timeElapsed, start, distance, this.duration);
        window.scrollTo(0, run);
        if (timeElapsed < this.duration) requestAnimationFrame(animation.bind(this));
      }

      function easeInOutQuad(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return c / 2 * t * t + b;
        t--;
        return -c / 2 * (t * (t - 2) - 1) + b;
      }

      requestAnimationFrame(animation.bind(this));
    }
  }

  // Enhanced HeaderManager with throttling and better performance
  class HeaderManager {
    constructor(headerSelector, shrinkClass = 'header-shrink', scrollThreshold = 100) {
      this.$header = $(headerSelector);
      this.shrinkClass = shrinkClass;
      this.scrollThreshold = scrollThreshold;
      this.lastScrollTop = 0;
      this.hideClass = 'header-hidden';
      this.init();
    }

    init() {
      // Throttle scroll event for better performance
      $(window).on('scroll', Utility.throttle(() => {
        this.handleScroll();
      }, 16)); // ~60fps

      // Handle resize
      $(window).on('resize', Utility.debounce(() => {
        this.handleResize();
      }, 250));
    }

    handleScroll() {
      const scrollTop = $(window).scrollTop();
      const headerHeight = this.$header.outerHeight();
      
      // Add/remove shrink class
      if (scrollTop > this.scrollThreshold) {
        this.$header.addClass(this.shrinkClass);
      } else {
        this.$header.removeClass(this.shrinkClass);
      }

      // Hide/show header based on scroll direction
      if (scrollTop > this.lastScrollTop && scrollTop > headerHeight) {
        // Scrolling down
        this.$header.addClass(this.hideClass);
      } else {
        // Scrolling up
        this.$header.removeClass(this.hideClass);
      }

      this.lastScrollTop = scrollTop;
    }

    handleResize() {
      // Reset header state on resize
      this.$header.removeClass(this.hideClass);
      this.handleScroll();
    }
  }

  // Enhanced DynamicContentLoader with loading states and error handling
  class DynamicContentLoader {
    constructor(triggerSelector, targetSelector, urlAttr = 'data-url', options = {}) {
      this.$trigger = $(triggerSelector);
      this.$target = $(targetSelector);
      this.urlAttr = urlAttr;
      this.options = {
        loadingText: options.loadingText || 'Loading...',
        errorText: options.errorText || 'Failed to load content.',
        replaceContent: options.replaceContent || false,
        autoLoad: options.autoLoad || false,
        ...options
      };
      this.isLoading = false;
      this.init();
    }

    init() {
      this.$trigger.on('click', (e) => {
        e.preventDefault();
        if (!this.isLoading) {
          this.loadContent($(e.currentTarget));
        }
      });

      if (this.options.autoLoad) {
        this.autoLoadOnScroll();
      }
    }

    loadContent($trigger) {
      const url = $trigger.attr(this.urlAttr);
      if (!url || this.isLoading) return;

      this.isLoading = true;
      this.setLoadingState($trigger, true);

      Utility.ajaxGet(url, (response) => {
        this.handleSuccess(response, $trigger);
      }, (xhr) => {
        this.handleError(xhr, $trigger);
      }).always(() => {
        this.isLoading = false;
        this.setLoadingState($trigger, false);
      });
    }

    handleSuccess(response, $trigger) {
      if (response.html) {
        if (this.options.replaceContent) {
          this.$target.html(response.html);
        } else {
          this.$target.append(response.html);
        }
        
        // Trigger custom event for new content
        this.$target.trigger('contentLoaded', [response.html]);
        
        // Hide trigger if it's a load-more button and no more content
        if ($trigger.hasClass('load-more') && response.noMoreContent) {
          $trigger.fadeOut();
        }
      } else {
        this.showError(this.options.errorText);
      }
    }

    handleError(xhr, $trigger) {
      let errorMessage = this.options.errorText;
      
      if (xhr.status === 404) {
        errorMessage = 'Content not found.';
      } else if (xhr.status === 403) {
        errorMessage = 'Access denied.';
      }
      
      this.showError(errorMessage);
      Utility.logError('Dynamic content load failed', { status: xhr.status, url: $trigger.attr(this.urlAttr) });
    }

    setLoadingState($trigger, loading) {
      if (loading) {
        $trigger.addClass('loading').prop('disabled', true);
        if ($trigger.is('button')) {
          $trigger.data('original-text', $trigger.text()).text(this.options.loadingText);
        }
      } else {
        $trigger.removeClass('loading').prop('disabled', false);
        if ($trigger.is('button') && $trigger.data('original-text')) {
          $trigger.text($trigger.data('original-text'));
        }
      }
    }

    showError(message) {
      const $error = $('<div class="content-error">' + message + '</div>');
      this.$target.append($error);
      $error.delay(3000).fadeOut(() => $error.remove());
    }

    autoLoadOnScroll() {
      $(window).on('scroll', Utility.throttle(() => {
        if (this.isLoading) return;
        
        const triggerBottom = this.$trigger.offset().top + this.$trigger.outerHeight();
        const windowBottom = $(window).scrollTop() + $(window).height();
        
        if (triggerBottom < windowBottom + 200) { // 200px threshold
          this.loadContent(this.$trigger);
        }
      }, 200));
    }
  }

  // New classes for additional functionality

  // Modal manager for popups and dialogs
  class ModalManager {
    constructor(options = {}) {
      this.options = {
        modalSelector: options.modalSelector || '.modal',
        triggerSelector: options.triggerSelector || '[data-modal]',
        closeSelector: options.closeSelector || '.modal-close',
        overlayClass: options.overlayClass || 'modal-overlay',
        activeClass: options.activeClass || 'modal-active',
        ...options
      };
      this.$modal = $(this.options.modalSelector);
      this.isOpen = false;
      this.init();
    }

    init() {
      // Open modal
      $(document).on('click', this.options.triggerSelector, (e) => {
        e.preventDefault();
        this.open($(e.currentTarget).data('modal'));
      });

      // Close modal
      $(document).on('click', this.options.closeSelector, () => this.close());
      $(document).on('click', `.${this.options.overlayClass}`, () => this.close());

      // Close on ESC key
      $(document).on('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });

      // Trap focus within modal
      $(document).on('keydown', (e) => {
        if (this.isOpen && e.key === 'Tab') {
          this.trapFocus(e);
        }
      });
    }

    open(content) {
      if (this.isOpen) return;

      this.$modal.html(content).addClass(this.options.activeClass);
      this.createOverlay();
      this.isOpen = true;
      
      // Focus first focusable element
      setTimeout(() => {
        const $focusable = this.$modal.find('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])').first();
        if ($focusable.length) $focusable.focus();
      }, 100);

      // Prevent body scroll
      $('body').css('overflow', 'hidden');
    }

    close() {
      if (!this.isOpen) return;

      this.$modal.removeClass(this.options.activeClass);
      this.removeOverlay();
      this.isOpen = false;
      
      // Restore body scroll
      $('body').css('overflow', '');
      
      // Return focus to trigger
      $(this.options.triggerSelector).first().focus();
    }

    createOverlay() {
      if (!$(`.${this.options.overlayClass}`).length) {
        $('<div class="' + this.options.overlayClass + '"></div>').insertAfter(this.$modal);
      }
    }

    removeOverlay() {
      $(`.${this.options.overlayClass}`).remove();
    }

    trapFocus(e) {
      const $focusable = this.$modal.find('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      const $first = $focusable.first();
      const $last = $focusable.last();

      if (e.shiftKey) {
        if (document.activeElement === $first[0]) {
          e.preventDefault();
          $last.focus();
        }
      } else {
        if (document.activeElement === $last[0]) {
          e.preventDefault();
          $first.focus();
        }
      }
    }
  }

  // Image lazy loading manager
  class LazyLoadManager {
    constructor(options = {}) {
      this.options = {
        imageSelector: options.imageSelector || 'img[data-src]',
        threshold: options.threshold || 200,
        loadedClass: options.loadedClass || 'loaded',
        ...options
      };
      this.images = [];
      this.init();
    }

    init() {
      this.loadImages();
      $(window).on('scroll', Utility.throttle(() => this.loadImages(), 200));
      $(window).on('resize', Utility.debounce(() => this.loadImages(), 250));
    }

    loadImages() {
      $(this.options.imageSelector).each((index, element) => {
        const $img = $(element);
        if (!$img.hasClass(this.options.loadedClass) && Utility.isElementInViewport($img[0])) {
          this.loadImage($img);
        }
      });
    }

    loadImage($img) {
      const src = $img.data('src');
      const srcset = $img.data('srcset');
      
      $img.on('load', () => {
        $img.addClass(this.options.loadedClass);
      }).on('error', () => {
        Utility.logError('Failed to load image', { src: src });
      });

      if (src) $img.attr('src', src);
      if (srcset) $img.attr('srcset', srcset);
    }
  }

  // Theme manager for dark/light mode
  class ThemeManager {
    constructor(options = {}) {
      this.options = {
        toggleSelector: options.toggleSelector || '[data-theme-toggle]',
        storageKey: options.storageKey || 'portfolio-theme',
        darkClass: options.darkClass || 'dark-theme',
        ...options
      };
      this.currentTheme = this.getStoredTheme() || 'light';
      this.init();
    }

    init() {
      this.applyTheme(this.currentTheme);
      
      $(document).on('click', this.options.toggleSelector, () => {
        this.toggleTheme();
      });

      // Listen for system theme changes
      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addListener((e) => {
          if (!this.getStoredTheme()) {
            this.applyTheme(e.matches ? 'dark' : 'light');
          }
        });
      }
    }

    toggleTheme() {
      const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
      this.setTheme(newTheme);
    }

    setTheme(theme) {
      this.currentTheme = theme;
      this.applyTheme(theme);
      this.storeTheme(theme);
    }

    applyTheme(theme) {
      if (theme === 'dark') {
        $('html').addClass(this.options.darkClass);
      } else {
        $('html').removeClass(this.options.darkClass);
      }
    }

    getStoredTheme() {
      return localStorage.getItem(this.options.storageKey);
    }

    storeTheme(theme) {
      localStorage.setItem(this.options.storageKey, theme);
    }
  }

  // Initialize everything when DOM is ready
  $(document).ready(() => {
    // Initialize existing components
    if ($('.contact-form').length) {
      new ContactFormManager('.contact-form');
    }
    
    new SmoothScrollManager('a[href^="#"]', 70);
    
    if ($('header').length) {
      new HeaderManager('header');
    }
    
    if ($('.load-more').length && $('#content-container').length) {
      new DynamicContentLoader('.load-more', '#content-container');
    }

    // Initialize new components
    if ($('.modal').length || $('[data-modal]').length) {
      new ModalManager();
    }

    if ($('img[data-src]').length) {
      new LazyLoadManager();
    }

    if ($('[data-theme-toggle]').length) {
      new ThemeManager();
    }

    // Log initialization
    Utility.logInfo('Portfolio JavaScript initialized successfully');
  });

})(jQuery, window, document);
