(define-key ctl-x-map "\^b" 'electric-buffer-list)
(define-key esc-map "g" 'goto-line)
(setq-default transient-mark-mode t)
(setq initial-scratch-message nil)
(setq make-backup-files nil)
(menu-bar-mode -1)
(setq inhibit-startup-message t)
(if (fboundp 'desktop-save-mode) (desktop-save-mode 1))
(custom-set-variables
 ;; Your init file should contain only one such instance.
 ;; If there are more than one, they won't work right.
 '(show-paren-mode t nil (paren)))
(custom-set-faces
 ;; Your init file should contain only one such instance.
 ;; If there are more than one, they won't work right.
 '(font-lock-comment-face ((default nil) (nil (:foreground "red")))))
