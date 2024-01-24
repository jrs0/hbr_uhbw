The asciidoctor-bibtex extension is great! However, I'm having an issue that is preventing it from working on Windows.

# Minimal problem

On Windows, after installing asciidoctor (version 2.0.20), and asciidoctor-bibtex (0.8.0), create the following minimal bibtex file `ref.bib`:

```
@article{urban2021assessing,
  title={Assessing the risks of bleeding vs thrombotic events in patients at high bleeding risk after coronary stent implantation: the ARC--high bleeding risk trade-off model},
  author={Urban, Philip and Gregson, John and Owen, Ruth and Mehran, Roxana and Windecker, Stephan and Valgimigli, Marco and Varenne, Olivier and Krucoff, Mitchell and Saito, Shigeru and Baber, Usman and others},
  journal={JAMA cardiology},
  volume={6},
  number={4},
  pages={410--419},
  year={2021},
  publisher={American Medical Association}
}
```

and the following document `test.adoc`:

```adoc
= Test

cite:[urban2021assessing]

bibliography::[]
```

On running `asciidoctor -r asciidoctor-bibtex test.adoc`, I get the following error:

```
asciidoctor: FAILED: C:/Users/john.scott/Documents/git/hbr_uhbw/docs/test.adoc: Failed to load AsciiDoc document - undefined method `to_citeproc' for an instance of String
  Use --trace to show backtrace
```

When adding `--trace`, I get:

```
C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `block in to_citeproc': asciidoctor: FAILED: C:/Users/john.scott/Documents/git/hbr_uhbw/docs/test.adoc: Failed to load AsciiDoc document - undefined method `to_citeproc' for an instance of String (NoMethodError)

      map { |n| n.to_citeproc(options) }
                 ^^^^^^^^^^^^
        from C:/Ruby33-x64/lib/ruby/3.3.0/forwardable.rb:240:in `each'
        from C:/Ruby33-x64/lib/ruby/3.3.0/forwardable.rb:240:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `map'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:172:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:69:in `block 
in convert!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:132:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:132:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:68:in `convert!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:55:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:610:in `to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/bibliography.rb:407:in `block in to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/bibliography.rb:407:in `map'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/bibliography.rb:407:in `to_citeproc'     
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-bibtex-0.8.0/lib/asciidoctor-bibtex/processor.rb:76:in `initialize'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-bibtex-0.8.0/lib/asciidoctor-bibtex/extensions.rb:96:in `new'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-bibtex-0.8.0/lib/asciidoctor-bibtex/extensions.rb:96:in `process'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:545:in `[]'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:545:in `block in parse'        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:544:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:544:in `parse'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/load.rb:84:in `load'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:78:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:190:in `block in convert_file'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:190:in `open'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:190:in `convert_file'   
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/cli/invoker.rb:129:in `block in invoke!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/cli/invoker.rb:112:in `each'       
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/cli/invoker.rb:112:in `invoke!'    
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/bin/asciidoctor:15:in `<top (required)>'
        from C:/Ruby33-x64/bin/asciidoctor:32:in `load'
        from C:/Ruby33-x64/bin/asciidoctor:32:in `<main>'
C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `block in to_citeproc': undefined method `to_citeproc' for an instance of String (NoMethodError)

      map { |n| n.to_citeproc(options) }
                 ^^^^^^^^^^^^
        from C:/Ruby33-x64/lib/ruby/3.3.0/forwardable.rb:240:in `each'
        from C:/Ruby33-x64/lib/ruby/3.3.0/forwardable.rb:240:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `map'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:172:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:69:in `block 
in convert!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:132:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:132:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:68:in `convert!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:55:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:610:in `to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/bibliography.rb:407:in `block in to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/bibliography.rb:407:in `map'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/bibliography.rb:407:in `to_citeproc'     
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-bibtex-0.8.0/lib/asciidoctor-bibtex/processor.rb:76:in `initialize'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-bibtex-0.8.0/lib/asciidoctor-bibtex/extensions.rb:96:in `new'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-bibtex-0.8.0/lib/asciidoctor-bibtex/extensions.rb:96:in `process'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:545:in `[]'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:545:in `block in parse'        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:544:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/document.rb:544:in `parse'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/load.rb:84:in `load'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:78:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:190:in `block in convert_file'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:190:in `open'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/convert.rb:190:in `convert_file'   
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/cli/invoker.rb:129:in `block in invoke!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/cli/invoker.rb:112:in `each'       
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/lib/asciidoctor/cli/invoker.rb:112:in `invoke!'    
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/asciidoctor-2.0.20/bin/asciidoctor:15:in `<top (required)>'
        from C:/Ruby33-x64/bin/asciidoctor:32:in `load'
        from C:/Ruby33-x64/bin/asciidoctor:32:in `<main>'
```

# Versions

I obtained all the dependencies by running `gem install asciidoctor-bibtex` in the powershell, which gave the following log:

```
PS H:\> gem install asciidoctor-bibtex
Fetching asciidoctor-bibtex-0.8.0.gem
Fetching citeproc-ruby-1.1.14.gem
Fetching bibtex-ruby-5.1.6.gem
Successfully installed citeproc-ruby-1.1.14
Successfully installed bibtex-ruby-5.1.6
Successfully installed asciidoctor-bibtex-0.8.0
Parsing documentation for citeproc-ruby-1.1.14
Installing ri documentation for citeproc-ruby-1.1.14
Parsing documentation for bibtex-ruby-5.1.6
Installing ri documentation for bibtex-ruby-5.1.6
Parsing documentation for asciidoctor-bibtex-0.8.0
Installing ri documentation for asciidoctor-bibtex-0.8.0
Done installing documentation for citeproc-ruby, bibtex-ruby, asciidoctor-bibtex after 4 seconds
3 gems installed
```



# More Testing

I thought initially the problem was with [bibtex-ruby](https://github.com/inukshuk/bibtex-ruby), because I was able to reproduce the same kind of issue by following the instructions on their readme page.

For example, running the following commands in `irb` (with bibtex-ruby version 5.1.6, as installed by asciidoctor-bibtex dependencies), I get:

```ruby
require 'bibtex'
# => true
b = BibTeX.open('./ref.bib')
# => #<BibTeX::Bibliography data=[26]>
b['urban2021assessing'].title
# => "Assessing the risks of bleeding vs thrombotic events in patients at high bleeding risk after coronary stent implantation: the ARC--high bleeding risk trade-off model"

# Skipping down to the citeproc bit
require 'citeproc'
# => true
CiteProc.process b[:urban2021assessing].to_citeproc, :style => :apa
```

The final line produces the following error:

```
C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `block in to_citeproc': undefined method `to_citeproc' for an instance of String (NoMethodError)

      map { |n| n.to_citeproc(options) }
                 ^^^^^^^^^^^^
        from C:/Ruby33-x64/lib/ruby/3.3.0/forwardable.rb:240:in `each'
        from C:/Ruby33-x64/lib/ruby/3.3.0/forwardable.rb:240:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `map'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/names.rb:81:in `to_citeproc'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:172:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:69:in `block in convert!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:132:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:132:in `each'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:68:in `convert!'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry/citeproc_converter.rb:55:in `convert'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/bibtex-ruby-5.1.6/lib/bibtex/entry.rb:610:in `to_citeproc'
        from (irb):6:in `<main>'
        from <internal:kernel>:187:in `loop'
        from C:/Ruby33-x64/lib/ruby/gems/3.3.0/gems/irb-1.11.0/exe/irb:9:in `<top (required)>'
        from C:/Ruby33-x64/bin/irb:33:in `load'
        from C:/Ruby33-x64/bin/irb:33:in `<main>'
```

However, if I remove all my packages:

```
PS H:\> gem uninstall asciidoctor-bibtex bibtex-ruby citeproc-ruby cls-styles
Gem 'cls-styles' is not installed
Successfully uninstalled asciidoctor-bibtex-0.8.0
Successfully uninstalled citeproc-ruby-1.1.14
Successfully uninstalled bibtex-ruby-5.1.6
```

and then reinstall just bibtex-ruby and citeproc-ruby (getting the latest versions):

```
PS H:\> gem install bibtex-ruby citeproc-ruby
Fetching bibtex-ruby-6.1.0.gem
Successfully installed bibtex-ruby-6.1.0
Parsing documentation for bibtex-ruby-6.1.0
Installing ri documentation for bibtex-ruby-6.1.0
Done installing documentation for bibtex-ruby after 1 seconds
Fetching citeproc-ruby-2.0.0.gem
Successfully installed citeproc-ruby-2.0.0
Parsing documentation for citeproc-ruby-2.0.0
Installing ri documentation for citeproc-ruby-2.0.0
Done installing documentation for citeproc-ruby after 0 seconds
2 gems installed
```

the problem seems to go away (when I run the same commands as above in `irb`):

```ruby
# ... same commands as above, ending with...

CiteProc.process b[:urban2021assessing].to_citeproc, :style => :apa
# => nil
```

Oddly, the command returns nil, when it should return a non-null entry (based on the bibtex-ruby) readme. I haven't figured out the discrepancy, but my main thought was just that the `to_citeproc` error had gone. That made me think maybe there is some kind of version issue?

# It works in Linux

Testing out using Linux Mint 21.1 Cinnamon, running:

```bash
# sudo gem install asciidoctor-bibtex
Fetching bibtex-ruby-5.1.6.gem
Fetching asciidoctor-bibtex-0.8.0.gem
Fetching csl-styles-1.0.1.11.gem
Fetching citeproc-ruby-1.1.14.gem
Successfully installed csl-styles-1.0.1.11
Successfully installed citeproc-ruby-1.1.14
Successfully installed bibtex-ruby-5.1.6
Successfully installed asciidoctor-bibtex-0.8.0
Parsing documentation for csl-styles-1.0.1.11
Installing ri documentation for csl-styles-1.0.1.11
Parsing documentation for citeproc-ruby-1.1.14
Installing ri documentation for citeproc-ruby-1.1.14
Parsing documentation for bibtex-ruby-5.1.6
Installing ri documentation for bibtex-ruby-5.1.6
Parsing documentation for asciidoctor-bibtex-0.8.0
Installing ri documentation for asciidoctor-bibtex-0.8.0
Done installing documentation for csl-styles, citeproc-ruby, bibtex-ruby, asciidoctor-bibtex after 0 seconds
4 gems installed
```

All the gem versions look the same as Windows to me (unless I missed something), but it does work on Linux (the minimal example above right at the top runs fine).

That made me think maybe it was a Ruby version issue -- on Linux, `ruby --version` gives `ruby 3.0.2p107 (2021-07-07 revision 0db68f0233) [x86_64-linux-gnu]`, and on Windows it gives ``

# Conclusion

Not knowing anything about Ruby, I'm not really sure what the issue is, but it looked like some kind of dependency thing. I wondered if you would be able to offer any insight or any workarounds? (Or point out if I did anything obviously wrong!)
