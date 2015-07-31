'use strict';

module.exports = function(grunt){
	require('jit-grunt')(grunt);
	require('time-grunt')(grunt);

	grunt.loadNpmTasks('grunt-shell-spawn');

	// Configurable paths
	var config = {
		tmp: '.tmp',
		base: 'couchpotato',
		css_dest: 'couchpotato/static/style/combined.min.css',
		scripts_vendor_dest: 'couchpotato/static/scripts/combined.vendor.min.js',
		scripts_base_dest: 'couchpotato/static/scripts/combined.base.min.js',
		scripts_plugins_dest: 'couchpotato/static/scripts/combined.plugins.min.js'
	};

	var vendor_scripts_files = [
		'couchpotato/static/scripts/vendor/mootools.js',
		'couchpotato/static/scripts/vendor/mootools_more.js',
		'couchpotato/static/scripts/vendor/form_replacement/form_check.js',
		'couchpotato/static/scripts/vendor/form_replacement/form_radio.js',
		'couchpotato/static/scripts/vendor/form_replacement/form_dropdown.js',
		'couchpotato/static/scripts/vendor/form_replacement/form_selectoption.js',
		'couchpotato/static/scripts/vendor/Array.stableSort.js',
		'couchpotato/static/scripts/vendor/history.js',
		'couchpotato/static/scripts/vendor/dynamics.js',
		'couchpotato/static/scripts/vendor/fastclick.js'
	];

	var scripts_files = [
		'couchpotato/static/scripts/library/uniform.js',
		'couchpotato/static/scripts/library/question.js',
		'couchpotato/static/scripts/library/scrollspy.js',
		'couchpotato/static/scripts/couchpotato.js',
		'couchpotato/static/scripts/api.js',
		'couchpotato/static/scripts/page.js',
		'couchpotato/static/scripts/block.js',
		'couchpotato/static/scripts/block/navigation.js',
		'couchpotato/static/scripts/block/header.js',
		'couchpotato/static/scripts/block/footer.js',
		'couchpotato/static/scripts/block/menu.js',
		'couchpotato/static/scripts/page/home.js',
		'couchpotato/static/scripts/page/settings.js',
		'couchpotato/static/scripts/page/about.js',
		'couchpotato/static/scripts/page/login.js'
	];

	grunt.initConfig({

		// Project settings
		config: config,

		// Make sure code styles are up to par and there are no obvious mistakes
		jshint: {
			options: {
				reporter: require('jshint-stylish'),
				unused: false,
				camelcase: false,
				devel: true
			},
			all: [
				'<%= config.base %>/{,**/}*.js',
				'!<%= config.base %>/static/scripts/vendor/{,**/}*.js',
				'!<%= config.base %>/static/scripts/combined.*.js'
			]
		},

		// Compiles Sass to CSS and generates necessary files if requested
		sass: {
			options: {
				compass: true,
				update: true,
				sourcemap: 'none'
			},
			server: {
				files: [{
					expand: true,
					cwd: '<%= config.base %>/',
					src: ['**/*.scss'],
					dest: '<%= config.tmp %>/styles/',
					ext: '.css'
				}]
			}
		},

		// Add vendor prefixed styles
		autoprefixer: {
			options: {
				browsers: ['last 2 versions'],
				remove: false,
				cascade: false
			},
			dist: {
				files: [{
					expand: true,
					cwd: '<%= config.tmp %>/styles/',
					src: '{,**/}*.css',
					dest: '<%= config.tmp %>/styles/'
				}]
			}
		},

		cssmin: {
			dist: {
				options: {
					keepBreaks: true
				},
				files: {
					'<%= config.css_dest %>': ['<%= config.tmp %>/styles/**/*.css']
				}
			}
		},

		uglify: {
			options: {
				mangle: false,
				compress: false,
				beautify: true,
				screwIE8: true
			},
			vendor: {
				files: {
					'<%= config.scripts_vendor_dest %>': vendor_scripts_files
				}
			},
			base: {
				files: {
					'<%= config.scripts_base_dest %>': scripts_files
				}
			},
			plugins: {
				files: {
					'<%= config.scripts_plugins_dest %>': ['<%= config.base %>/core/**/*.js']
				}
			}
		},

		shell: {
			runCouchPotato: {
				command: 'python CouchPotato.py',
				options: {
					stdout: true,
					stderr: true
				}
			}
		},

		// COOL TASKS ==============================================================
		watch: {
			scss: {
				files: ['<%= config.base %>/**/*.{scss,sass}'],
				tasks: ['sass:server', 'autoprefixer', 'cssmin']
			},
			js: {
				files: [
					'<%= config.base %>/**/*.js',
					'!<%= config.base %>/static/scripts/combined.*.js'
				],
				tasks: ['uglify:base', 'uglify:plugins', 'jshint']
			},
			livereload: {
				options: {
					livereload: 35729
				},
				files: [
					'<%= config.css_dest %>',
					'<%= config.scripts_vendor_dest %>',
					'<%= config.scripts_base_dest %>',
					'<%= config.scripts_plugins_dest %>'
				]
			}
		},

		concurrent: {
			options: {
				logConcurrentOutput: true
			},
			tasks: ['shell:runCouchPotato', 'watch']
		}

	});

	grunt.registerTask('default', ['sass:server', 'autoprefixer',  'cssmin', 'uglify:vendor', 'uglify:base', 'uglify:plugins', 'concurrent']);

};
