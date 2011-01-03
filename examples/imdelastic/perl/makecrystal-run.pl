#!/usr/bin/perl
use Cwd;
use File::Path;
use sigtrap 'handler', \&cleanup , 'error-signals' ;
$SIG{PIPE}=\&trap; $SIG{QUIT}=\&trap; $SIG{INT}=\&trap; $SIG{STOP}=\&trap; $SIG{HUP}=\&trap;

sub trap
{
        debug( "Stop!" ) ;
        &cleanup ;
}

my ( $mode , $out_file , $box_file , $x , $y , $z , $crack_len , $crack_slope , $vacum_space , $xstrain , $colX , $colY , $png_file ) = @ARGV ; 
my $cmd = '' ;
if( $mode eq 'crack' )
{
	$cmd = 'fcc_110-crack' ;
}
elsif( $mode eq 'elastic' )
{
	$cmd = 'fcc_110-elastic' ;
}
elsif( $mode eq 'nanowire' )
{
	$cmd = 'fcc_110-nanowire' ;
}
else
{
	print "Usage: $0 mode out_file box_file x y z cracklen crackslope vacspace xstrain\n" ;
	die "Unknown mode" ;
}
chomp( my $dir = `dirname $0` ) ;

my $tmp = $cmd . '_stdout.txt' ;
if( -f "$dir/$cmd" )
{
	`cp $dir/$cmd /tmp/$$.$cmd` ;
	`chmod 755 /tmp/$$.$cmd` ;
	open FILE , "| /tmp/$$.$cmd > $tmp" ;
	print FILE <<EOF;
$out_file
$x
$y
$z
$crack_len
$crack_slope
$vacum_space
$xstrain
EOF
	close FILE ;
	unlink "/tmp/$$.$cmd" ;
system( "grep box_ $tmp > $box_file" ) ;
my $colZ = $colY+1 ;
`cp $dir/gnuplot /tmp/$$.gnuplot` ; 
`chmod 755 /tmp/$$.gnuplot` ;

chomp( my $xmin = `awk "-F " '{print\$$colX}' $out_file | sort -n | head -1` ) ;
chomp( my $xmax = `awk "-F " '{print\$$colX}' $out_file | sort -n -r | head -1` ) ;
chomp( my $ymin = `awk "-F " '{print\$$colY}' $out_file | sort -n | head -1` ) ;
chomp( my $ymax = `awk "-F " '{print\$$colY}' $out_file | sort -n -r | head -1` ) ;
chomp( my $zmin = `awk "-F " '{print\$$colZ}' $out_file | sort -n | head -1` ) ;
chomp( my $zmax = `awk "-F " '{print\$$colZ}' $out_file | sort -n -r | head -1` ) ;

my $dx = ( $xmax - $xmin ) ;
my $dy = ( $ymax - $ymin ) ;
my $dz = ( $zmax - $zmin ) ;

my $dd = (( $dx > $dy ) ? $dx : $dy ) ;
my $dd = (( $dz > $dd ) ? $dz : $dd ) ;

print "$xmin $xmax\n$ymin $ymax\n$zmin $zmax\n$dx $dy $dz\n$dd\n" ;
 
$xmax = $xmin + $dd ;
$ymax = $ymin + $dd ;
$zmax = $zmin + $dd ;

print "\n\n$xmin $xmax\n$ymin $ymax\n$zmin $zmax\n" ;

close FILE ;

=head
open FILE , "| /tmp/$$.gnuplot > $png_file" ;
print FILE <<EOF;
set term png
set size square
set title "$mode"
plot "$out_file" using $colX:$colY
EOF
close FILE ;
=cut

open FILE , "| /tmp/$$.gnuplot > XY_$png_file" ;
print FILE <<EOF;
set term png
set size square
set xrange [$xmin:$xmax] 
set yrange [$ymin:$ymax]
set title "$mode"
plot "$out_file" using $colX:$colY
EOF
close FILE ;

open FILE , "| /tmp/$$.gnuplot > XZ_$png_file" ;
print FILE <<EOF;
set term png
set size square
set xrange [$xmin:$xmax] 
set yrange [$zmin:$zmax] 
set title "$mode"
plot "$out_file" using $colX:$colZ
EOF
close FILE ;

open FILE , "| /tmp/$$.gnuplot > YZ_$png_file" ;
print FILE <<EOF;
set term png
set xrange [$ymin:$ymax] 
set yrange [$zmin:$zmax] 
set title "$mode"
plot "$out_file" using $colY:$colZ
EOF
close FILE ;

open FILE , "| /tmp/$$.gnuplot > XYZ_$png_file" ;
print FILE <<EOF;
set term png
set xrange [$xmin:$xmax] 
set yrange [$ymin:$ymax] 
set zrange [$zmin:$zmax] 
set title "$mode"
splot "$out_file" using $colX:$colY:$colZ w dots
EOF
close FILE ;

unlink "/tmp/$$.gnuplot" ;
}
else
{
	die "Command missing: $dir/$cmd\n" ;
}


sub cleanup
{
	$cwd = getcwd ;
	rmtree($cwd);
	unlink "/tmp/$$.gnuplot" ;
	`echo "cleanup in makecrystal" >> /home/gpserver/iran`;
	exit;
}

sub debug
{
        print STDERR join( "\n" , @_ ) . "\n" ;
        open FILE , ">>myError.log" ;
        print FILE join( "\n" , @_ ) . "\n" ;
        close FILE ;
}

