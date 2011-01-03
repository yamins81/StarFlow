#!/usr/bin/perl
use sigtrap 'handler', \&cleanup , 'error-signals' ;
$SIG{PIPE}=\&trap; $SIG{QUIT}=\&trap; $SIG{INT}=\&trap; $SIG{STOP}=\&trap; $SIG{HUP}=\&trap;
use Cwd;
use File::Copy;
use File::Basename;
use Sys::Hostname;
$ENV{'LD_LIBRARY_PATH'} = '/home/gpserver/materials/src/gd/lib';

sub trap
{
        debug( "Stop!" ) ;
        &cleanup ;
}

my ($zip , $movie , $delay , $colX , $colY , $vecX , $vecY , $energy_col , $energy_cut) = @ARGV ;
=head
my $zip = "Checkpoints.zip" ;
my $movie = "Movie.gif" ;
my $delay = 10 ;
my $colX = 4 ;
my $colY = 5 ;
my $vecX = $colX + 3 ;
my $vecY = $colY + 3 ;
my $energy_col = 10 ;
my $energy_cut = -2 ;
=cut
print "Args = " . join( " " , @ARGV ) ;
my $tmp = "/scratch/sgeadmin";
my $cwd = getcwd();
my $hostname = hostname();
my $dir = dirname($0) ;

open (FILE,">$cwd/mycwd");
print FILE "$hostname\n";
print FILE "$tmp/$$\n";
close (FILE);
copy("$cwd/mycwd","/home/gpserver/examplefile");

if ($dir eq '' ) { $dir = '.' ; }

mkdir("$tmp/$$");
copy("$cwd/$zip","$tmp/$$/");
chdir("$tmp/$$");
`unzip $zip` ;
copy("$dir/gnuplot", "$tmp/$$/$$.gnuplot") ;
chmod 0755, "$tmp/$$/$$.gnuplot" ;


chomp( my $Xmax = `cat *.chkpt | awk '{print\$$colX}' | sort -r -n | head -1` ) ;
chomp( my $Ymax = `cat *.chkpt | awk '{print\$$colY}' | sort -r -n | head -1` ) ;
chomp( my $Xmin = `cat *.chkpt | awk '{print\$$colX}' | sort -n | head -1` ) ;
chomp( my $Ymin = `cat *.chkpt | awk '{print\$$colY}' | sort -n | head -1` ) ;

my $dx = $Xmax - $Xmin ;
my $dy = $Ymax - $Ymin ;

if( $dx > $dy )
{
	$Ymax = $Ymin + $dx ;
}
else
{
	$Xmax = $Xmin + $dy ;
}
$Xmax += 1 ;
$Xmin -= 1 ;
$Ymax += 1 ;
$Ymin -= 1 ;

my @files = <*.chkpt>;
foreach my $file ( @files )
{
	my $png_file = "$file.png" ;
	my $out_file = "$file.filt" ; 
	&filter( $file , $out_file , $energy_cut , $energy_col ) ;
	print "$file\n" ;
	open FILE , "| $tmp/$$/$$.gnuplot > $png_file" ;
print FILE <<EOF;
set term png
set size square
set title "$file"
set xrange [$Xmin:$Xmax] 
set yrange [$Ymin:$Ymax] 
plot "$out_file" using $colX:$colY:(\$$vecX*10):(\$$vecY*10) w vector
EOF
	close FILE ;
	`cat $out_file >> $movie.xyz` ;
	`bash $dir/run_py.sh $out_file` ;
	`zip $movie.xyz.zip $out_file $out_file.xyz` ;
	unlink $out_file ;
}
unlink "$tmp/$$/$$.gnuplot" ;
copy("$dir/convert", "$tmp/$$/$$.convert") ;
chmod 0775, "$tmp/$$/$$.convert" ;
my $last = $files[ -1 + scalar @files ] ;
`export LD_LIBRARY_PATH=$dir ; $tmp/$$/$$.convert -delay $delay Out*.chkpt.png -delay 300 $last.png $movie` ;
unlink("$tmp/$$/$$.convert");
my @tmpfiles = <*.png>;
push @tmpfiles, <*.chkpt>, <*.chkpt.xyz>, <*.chkpt.filt.xyz>;
unlink @tmpfiles;
move("$movie.xyz", "$movie.txt") ;

foreach (<$tmp/$$/*>) {
	move($_,$cwd);
}

#`mv $tmp/$$/* $cwd/`;

rmdir("$tmp/$$");

sub filter
{
	my ( $in , $out , $value , $column ) = @_ ;
	open IN , $in ;
	open OUT , ">$out" ;
	while( $line = <IN> )
	{
		if( $line =~ /^#/ )
		{
			next ;
		}
		my ( @array ) = split( / +/ , $line ) ;
		if( $array[ $column - 1 ] > $value )
		{
			print OUT $line ;
		}
	}
	close IN ;
	close OUT ;
}

sub cleanup
{

        &debug( "removing $cwd\n" ) ;
	$cwd = getcwd;
	rmtree($cwd);
        &debug( "removing $tmp/$$\n" ) ;
	rmtree("$tmp/$$");
	`echo "cleanup in make_movie.pl" >> /home/gpserver/iran"`;
	exit;
}

sub debug
{
        print STDERR join( "\n" , @_ ) . "\n" ;
        open FILE , ">>myError.log" ;
        print FILE join( "\n" , @_ ) . "\n" ;
        close FILE ;
}

